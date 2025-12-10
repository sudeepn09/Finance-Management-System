// static/js/main.js

document.addEventListener("DOMContentLoaded", function () {

    // ====================================================
    // THEME TOGGLE (light / dark)
    // ====================================================
    const htmlEl = document.documentElement;
    const themeToggle = document.getElementById("theme-toggle");

    function applyTheme(theme) {
        htmlEl.setAttribute("data-theme", theme);
        localStorage.setItem("sgf-theme", theme);
    }

    const savedTheme = localStorage.getItem("sgf-theme") || "light";
    applyTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const current = htmlEl.getAttribute("data-theme") || "light";
            applyTheme(current === "light" ? "dark" : "light");
        });
    }

    // ====================================================
    // SIDEBAR TOGGLE (mobile)
    // ====================================================
    const sidebar = document.querySelector(".sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const menuButton = document.getElementById("menu-button");

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("hidden");
    }

    function openSidebar() {
        if (sidebar) sidebar.classList.add("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("hidden");
    }

    if (menuButton && sidebar && sidebarBackdrop) {
        menuButton.addEventListener("click", openSidebar);
        sidebarBackdrop.addEventListener("click", closeSidebar);
    }

    // ====================================================
    // REALTIME CLOCK (header + login)
    // ====================================================
    function updateClock() {
        const clock = document.getElementById("realtime-clock");
        const clockLogin = document.getElementById("realtime-clock-login");
        const now = new Date();

        const pad = (n) => (n < 10 ? "0" + n : "" + n);

        const dd = pad(now.getDate());
        const mm = pad(now.getMonth() + 1);
        const yyyy = now.getFullYear();

        let hh = now.getHours();
        const ampm = hh >= 12 ? "PM" : "AM";
        hh = hh % 12;
        if (hh === 0) hh = 12;
        const min = pad(now.getMinutes());
        const ss = pad(now.getSeconds());

        const text = `${dd}-${mm}-${yyyy}  ${pad(hh)}:${min}:${ss} ${ampm}`;

        if (clock) clock.textContent = text;
        if (clockLogin) clockLogin.textContent = text;
    }

    updateClock();
    setInterval(updateClock, 1000);

    // ====================================================
    // HEADER SEARCH (account no / mobile)
    // ====================================================
    const headerSearchForm = document.getElementById("header-search-form");
    const headerSearchInput = document.getElementById("header-search-input");

    if (headerSearchForm && headerSearchInput) {
        headerSearchForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const q = headerSearchInput.value.trim();
            if (!q) return;

            fetch(`/search_member?q=${encodeURIComponent(q)}`)
                .then((r) => r.json())
                .then((data) => {
                    if (!data.success) {
                        alert("Member not found");
                        return;
                    }
                    // Go to member page and let user see details
                    window.location.href = `/member?account_no=${encodeURIComponent(
                        data.member.account_no
                    )}`;
                })
                .catch(() => {
                    alert("Error searching member.");
                });
        });
    }

    // ====================================================
    // SETTINGS PAGE – SECTION TOGGLE
    // ====================================================
    const navBtns = document.querySelectorAll(".settings-nav-btn");
    const sectionCards = document.querySelectorAll(".settings-section-card");
    const toggles = document.querySelectorAll(".settings-toggle");

    function showSettingsSection(id) {
        sectionCards.forEach((card) => {
            if (card.id === id) {
                card.classList.remove("collapsed");
            } else {
                card.classList.add("collapsed");
            }
        });
    }

    navBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-target");
            if (target) showSettingsSection(target);
        });
    });

    toggles.forEach((btn) => {
        btn.addEventListener("click", () => {
            const card = btn.closest(".settings-section-card");
            if (!card) return;
            card.classList.toggle("collapsed");
        });
    });

    // ====================================================
    // GENERIC PRINT SECTION HELPER (for member, etc.)
    // ====================================================
    window.printSection = function (id) {
        const el = document.getElementById(id);
        if (!el) {
            window.print();
            return;
        }
        const original = document.body.innerHTML;
        const clone = el.outerHTML;
        document.body.innerHTML = clone;
        window.print();
        document.body.innerHTML = original;
        window.location.reload();
    };

    // ====================================================
    // LOAN PAGE: AUTO MEMBER NAME + AUTO EMI + END DATE
    // ====================================================
    const accInput   = document.getElementById("loan-account-no");
    const nameInput  = document.getElementById("loan-member-name");

    const loanTypeEl   = document.getElementById("loan-type");
    const principalEl  = document.getElementById("loan-principal");
    const rateEl       = document.getElementById("loan-interest-rate");
    const instEl       = document.getElementById("loan-installments");
    const emiEl        = document.getElementById("loan-emi");
    const startDateEl  = document.getElementById("loan-start-date");
    const endDateEl    = document.getElementById("loan-end-date");

    // ---- Auto Member Name for LOAN page (special fields) ----
    function loadMemberName() {
        if (!accInput || !nameInput) return;
        const val = accInput.value.trim();
        if (!val) {
            nameInput.value = "";
            return;
        }
        fetch(`/api/member_name?account_no=${encodeURIComponent(val)}`)
            .then((r) => r.json())
            .then((data) => {
                if (data.success) {
                    nameInput.value = data.name;
                } else {
                    nameInput.value = "";
                }
            })
            .catch(() => {
                nameInput.value = "";
            });
    }

    if (accInput && nameInput) {
        accInput.addEventListener("change", loadMemberName);
        accInput.addEventListener("blur", loadMemberName);
        accInput.addEventListener("keyup", function (e) {
            if (e.key === "Enter") {
                loadMemberName();
            }
        });
    }

    // ---- Auto EMI & End Date ----
    function recalcEMIAndEndDate() {
        if (!loanTypeEl || !principalEl || !rateEl || !instEl || !emiEl || !startDateEl || !endDateEl) return;

        const principal = parseFloat(principalEl.value) || 0;
        const rate = parseFloat(rateEl.value) || 0;
        const inst = parseInt(instEl.value || "0", 10);
        const loanType = loanTypeEl.value;

        let years = 0;
        if (inst > 0) {
            if (loanType === "Weekly") {
                years = inst / 52.0;
            } else if (loanType === "Yearly") {
                years = inst;
            } else {
                years = inst / 12.0; // Monthly, FD Loan
            }
        }

        let totalInterest = 0;
        if (principal > 0 && rate > 0 && years > 0) {
            totalInterest = principal * (rate / 100.0) * years;
        }
        const totalPayable = principal + totalInterest;

        let emi = 0;
        if (inst > 0) {
            emi = totalPayable / inst;
        }
        emiEl.value = emi > 0 && !isNaN(emi) ? emi.toFixed(2) : "";

        // ---- End Date based on Start Date + Tenure ----
        const startVal = startDateEl.value;
        if (startVal && inst > 0) {
            const d = new Date(startVal);
            if (!isNaN(d.getTime())) {
                if (loanType === "Weekly") {
                    d.setDate(d.getDate() + inst * 7);
                } else {
                    d.setDate(d.getDate() + inst * 30);
                }
                const year  = d.getFullYear();
                const month = String(d.getMonth() + 1).padStart(2, "0");
                const day   = String(d.getDate()).padStart(2, "0");
                endDateEl.value = `${year}-${month}-${day}`;
            } else {
                endDateEl.value = "";
            }
        } else {
            endDateEl.value = "";
        }
    }

    // Set Start Date to today if empty (safety)
    if (startDateEl && !startDateEl.value) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm   = String(today.getMonth() + 1).padStart(2, "0");
        const dd   = String(today.getDate()).padStart(2, "0");
        startDateEl.value = `${yyyy}-${mm}-${dd}`;
    }

    if (loanTypeEl && principalEl && rateEl && instEl && startDateEl) {
        loanTypeEl.addEventListener("change", recalcEMIAndEndDate);
        principalEl.addEventListener("input", recalcEMIAndEndDate);
        rateEl.addEventListener("input", recalcEMIAndEndDate);
        instEl.addEventListener("input", recalcEMIAndEndDate);
        startDateEl.addEventListener("change", recalcEMIAndEndDate);
    }

    // Initial calculation when page loads
    recalcEMIAndEndDate();

        // ====================================================
    // GENERIC AUTO MEMBER NAME (Debit / Credit forms)
    // ====================================================
    function autoFillNameFor(inp) {
        const val = inp.value.trim();
        const form = inp.closest("form");
        if (!form) return;

        // 1) Prefer field marked with data-member-name
        let nameField = form.querySelector('[data-member-name]');
        // 2) Fallback to name="name"
        if (!nameField) {
            nameField = form.querySelector('input[name="name"]');
        }
        // 3) Final fallback: any input whose id looks like "*name*"
        if (!nameField) {
            nameField = form.querySelector('input[id*="name"]');
        }

        if (!nameField) return;

        if (!val) {
            nameField.value = "";
            return;
        }

        fetch(`/api/member_name?account_no=${encodeURIComponent(val)}`)
            .then((r) => r.json())
            .then((data) => {
                if (data.success) {
                    nameField.value = data.name;
                } else {
                    nameField.value = "";
                }
            })
            .catch(() => {
                nameField.value = "";
            });
    }

    // Attach to all account_no inputs EXCEPT loan page (already handled)
    const accountInputs = document.querySelectorAll('input[name="account_no"]');
    accountInputs.forEach((inp) => {
        if (inp.id === "loan-account-no") {
            return; // loan uses special handler above
        }
        inp.addEventListener("change", () => autoFillNameFor(inp));
        inp.addEventListener("blur", () => autoFillNameFor(inp));
        inp.addEventListener("keyup", (e) => {
            if (e.key === "Enter") {
                autoFillNameFor(inp);
            }
        });
    });

});


    // Attach to all account_no inputs EXCEPT loan page (already handled)
    const accountInputs = document.querySelectorAll('input[name="account_no"]');
    accountInputs.forEach((inp) => {
        if (inp.id === "loan-account-no") {
            return; // loan uses special handler above
        }
        inp.addEventListener("change", () => autoFillNameFor(inp));
        inp.addEventListener("blur", () => autoFillNameFor(inp));
        inp.addEventListener("keyup", (e) => {
            if (e.key === "Enter") {
                autoFillNameFor(inp);
            }
        });
    });


