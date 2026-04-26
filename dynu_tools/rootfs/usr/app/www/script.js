document.addEventListener("DOMContentLoaded", () => {
    const apiKeyInput = document.getElementById("api_key");
	const emailInput = document.getElementById("email");
	const passwordInput = document.getElementById("password");
    const saveSettingsBtn = document.getElementById("save_settings");

    const domainsContainer = document.getElementById("domains");
    const saveDomainsBtn = document.getElementById("save_domains");
	const refreshDomainsBtn = document.getElementById("refresh_domains");

    let domainData = {};

    // Load both settings and domains on startup
    loadSettings();
    loadDomains();

    // -----------------------------
    // Load API key
    // -----------------------------
    async function loadSettings() {
		let base = window.location.pathname;
        const res = await fetch(base + "/api/settings");
        const data = await res.json();
        apiKeyInput.value = data.api_key || "";
		emailInput.value = data.email || "";
		passwordInput.value = data.password || "";
    }

    // -----------------------------
    // Save API key + refresh domains
    // -----------------------------
    saveSettingsBtn.addEventListener("click", async () => {
        const api_key = apiKeyInput.value.trim();
		const email = emailInput.value.trim();
		const password = passwordInput.value.trim();
		
		if (email != "" && !isValidEmail(email)) {
			alert("Invalid email address entered");
			return;
		}
		
		let base = window.location.pathname;
        await fetch(base + "/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key, email, password })
        });

        // Refresh domains after API key change
        await loadDomains();
    });

    // -----------------------------
    // Load full domains.json
    // -----------------------------
    async function loadDomains() {
		domainsContainer.innerHTML = "";
		const heading = document.createElement("h1");
        heading.textContent = "Loading Domain List";
        domainsContainer.appendChild(heading);
		let base = window.location.pathname;
        const res = await fetch(base + "/api/domains");
        domainData = await res.json();
		if (domainData.error) {
			domainsContainer.innerHTML = "";
			const heading = document.createElement("h1");
			heading.textContent = "Error loading Domains - " + domainData.error;
			domainsContainer.appendChild(heading);
		} else {
			renderDomains(domainData);
		}
    }

    // -----------------------------
    // Render domain tables
    // -----------------------------
    function renderDomains(data) {
        domainsContainer.innerHTML = "";
		
		const disableCert = emailInput.value.trim() === "";
		const disableUpdate = passwordInput.value.trim() === "";
		
		const hasDomains = data.domains && Object.keys(data.domains).length > 0;

		// Hide or show the Refresh button
		refreshDomainsBtn.style.display = hasDomains ? "inline-block" : "none";

		if (!hasDomains) {
			const heading = document.createElement("h3");
			if (apiKeyInput.value == "") {
				heading.textContent = "Please enter an API Key";
			} else {
				heading.textContent = "No domains loaded";
			}
			domainsContainer.appendChild(heading);
			return; // Nothing to render
		}
			
		const heading = document.createElement("h1");
        heading.textContent = "Domains";
        domainsContainer.appendChild(heading);
		
		for (const domainName of data.sort_order) {
			const domainObj = data.domains[domainName];
			
			const enableV6 = domainObj["ipv6_enabled"];
			const ipv6_connection = domainObj["ipv6_connection"];
			const wildcardV4 = domainObj["wildcards"].ipv4;
			const wildcardV6 = domainObj["wildcards"].ipv6;
	
            const wrapper = document.createElement("div");
            wrapper.className = "domain-block";

            const title = document.createElement("h2");
            title.textContent = domainName;
            wrapper.appendChild(title);
			
			const domain_settings = document.createElement("h4");
            domain_settings.textContent = "(IPv6: ";
			if (enableV6) {
				if (ipv6_connection) {
					domain_settings.textContent += "Enabled";
				} else {
					domain_settings.textContent += "Host IPv6 Failed";
				}
			} else {
				domain_settings.textContent += "Disabled";
			}
			domain_settings.textContent += ", IPv4 Wildcard: ";			
			if (wildcardV4) {
				domain_settings.textContent += "Enabled";
			} else {
				domain_settings.textContent += "Disabled";
			}
			domain_settings.textContent += ", IPv6 Wildcard: ";			
			if (enableV6 && wildcardV6) {
				domain_settings.textContent += "Enabled";
			} else {
				domain_settings.textContent += "Disabled";
			}
			domain_settings.textContent += ")";
			
            wrapper.appendChild(domain_settings);

            const table = document.createElement("table");
            table.innerHTML = `
                <tr>
                    <th>Hostname</th>
                    <th>IPv4</th>
                    <th>IPv6</th>
                    <th class="checkbox-cell">Update IPv4</th>
                    <th class="checkbox-cell">Update IPv6</th>
                    <th class="checkbox-cell">Certificate</th>
					<th></th>
                </tr>
            `;

			for (const hostname of data.domains[domainName].sort_order) {
				const rec = data.domains[domainName].records[hostname];

                const row = document.createElement("tr");
				const deleteButton = rec.custom
					? `<button class="delete-custom" data-domain="${domainName}" data-host="${hostname}">Delete</button>`
					: "";
				const ipv4Check = !rec.custom
					? `<input type="checkbox" ${rec.update_ipv4 && !disableUpdate ? "checked" : ""} ${disableUpdate ? "disabled" : ""}>`
					: "";
				const ipv6Check = !rec.custom
					? `<input type="checkbox" ${rec.update_ipv6 && !disableUpdate && enableV6 && ipv6_connection ? "checked" : ""} ${disableUpdate || rec.custom || !enableV6 || !ipv6_connection ? "disabled" : ""}>`
					: "";
				
				let wild = false;
				
				for (const checkhost of data.domains[domainName].sort_order) {
					if (hostname != checkhost && checkhost.startsWith("*")) {
						const l1 = hostname.split(".");
						const l2 = checkhost.split(".");
						if (l1.length == l2.length) {
							let isMatch = true;
							for (let i = l1.length-1; i > 0; i--) {
								if (l1[i] != l2[i]) {
									isMatch = false;
									break
								}
							}
							if (isMatch && data.domains[domainName].records[checkhost].certificate) {
								rec.certificate = false;
								wild = true;
								break
							}
						}
					}
				}

                row.innerHTML = `
                    <td>${hostname}</td>
                    <td>${rec.ipv4 === null || rec.ipv4 === "" ? "N/A" : rec.ipv4}</td>
                    <td>${rec.ipv6 === null || rec.ipv6 === "" ? "N/A" : rec.ipv6}</td>
                    <td class="checkbox-cell">${ipv4Check}</td>
                    <td class="checkbox-cell">${ipv6Check}</td>
					<td class="checkbox-cell"><input type="checkbox" ${rec.certificate && !disableCert ? "checked" : ""} ${disableCert || wild ? "disabled" : ""}></td>
					<td class="checkbox-cell">${deleteButton}</td>
                `;
				
				const [ipv4Box, ipv6Box, certBox] = row.querySelectorAll("input");

				if (!rec.custom) {
					const [ipv4Box, ipv6Box, certBox] = row.querySelectorAll("input");
					
					ipv4Box.addEventListener("change", () => {
						rec.update_ipv4 = ipv4Box.checked;
						saveDomainsBtn.style.display = "inline-block";
					});

					ipv6Box.addEventListener("change", () => {
						rec.update_ipv6 = ipv6Box.checked;
						saveDomainsBtn.style.display = "inline-block";
					});
					
					certBox.addEventListener("change", () => {
						rec.certificate = certBox.checked;
						renderDomains(domainData)
						saveDomainsBtn.style.display = "inline-block";
					});
				} else {
					const [certBox] = row.querySelectorAll("input");
					
					certBox.addEventListener("change", () => {
						rec.certificate = certBox.checked;
						renderDomains(domainData)
						saveDomainsBtn.style.display = "inline-block";
					});
				}

                table.appendChild(row);
            }
			
			if (!disableCert) {
				const row = document.createElement("tr");
				
				row.innerHTML = `
					<td><input type="text" title="Enter a custom hostname to include in certificate" class="hostname-input"></td>
					<td></td>
					<td></td>
					<td class="checkbox-cell"></td>
					<td class="checkbox-cell"></td>
					<td class="checkbox-cell"><input type="checkbox" checked disabled></td>
					<td class="checkbox-cell"><button class="add-custom" data-domain="${domainName}">Add</button></td>
				`;

				table.appendChild(row);
			}

            wrapper.appendChild(table);

            domainsContainer.appendChild(wrapper);
        }
    }
	
	function isValidEmail(email) {
		const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
		return regex.test(email);
	}

	function isValidLabel(label) {
		if (!label || label.length > 63) return false;
		return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(label);
	}
	
	function isValidHostname(hostname) {
		if (!hostname || hostname.length > 253) return false;

		const labels = hostname.trim().toLowerCase().split(".");

		// Reject empty labels (e.g., "alpha..mx")
		if (labels.some(l => l.length === 0)) return false;

		// Wildcard case
		if (labels[0] === "*") {
			// Remaining labels must be normal
			return labels.slice(1).every(isValidLabel);
		}

		// No wildcard → all labels must be normal
		return labels.every(isValidLabel);
	}

	
	domainsContainer.addEventListener("click", (e) => {
		if (e.target.classList.contains("add-custom")) {
			const domainName = e.target.dataset.domain;

			// Find the row the button is in
			const row = e.target.closest("tr");
			
			// Find the input inside that row
			const input = row.querySelector(".hostname-input");

			// Find the input inside that row
			const hostname = input.value.trim().toLowerCase();

			if (!isValidHostname(hostname) || !hostname.endsWith(domainName)) {
				alert("Invalid hostname entered");
				return;
			}
			
			for (const existingHost of domainData.domains[domainName].sort_order) {
				if (existingHost.toLowerCase() == hostname) {
					alert("Duplicate hostname entered");
					return;
				}
			}

			// Add to JSON
			domainData.domains[domainName].records[hostname] = {
				ipv4: null,
				ipv6: null,
				update_ipv4: false,
				update_ipv6: false,
				certificate: true,
				custom: true
			};
			
			domainData.domains[domainName].sort_order.push(hostname);

			// Re-render UI
			renderDomains(domainData)
			saveDomainsBtn.style.display = "inline-block"
		} else if (e.target.classList.contains("delete-custom")) {

			const domainName = e.target.dataset.domain;
			const hostName = e.target.dataset.host;
			
			domainData.domains[domainName].sort_order = domainData.domains[domainName].sort_order.filter(r => r !== hostName);

			delete domainData.domains[domainName].records[hostName];

			renderDomains(domainData)
			saveDomainsBtn.style.display = "inline-block";
		}
	});


    // -----------------------------
    // Save full domains.json
    // -----------------------------
    saveDomainsBtn.addEventListener("click", async () => {
        let base = window.location.pathname;
		await fetch(base + "/api/domains", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(domainData)
        });

        alert("Domains saved");
		saveDomainsBtn.style.display = "none";
    });
	
	refreshDomainsBtn.addEventListener("click", async () => {
		loadDomains();
		saveDomainsBtn.style.display = "none";
		refreshDomainsBtn.style.display = "none";
    });
});
