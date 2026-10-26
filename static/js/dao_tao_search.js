/**
 * Cake Crush HR - Searchable Select Component
 * Chuyển đổi thẻ <select> thành ô tìm kiếm trực tiếp từ bàn phím với dropdown kết quả lọc tức thì.
 */
function initSearchableSelect(selectEl, customPlaceholder) {
    if (!selectEl) return null;
    if (selectEl.dataset.searchableInit === "true") {
        if (selectEl.refreshSearchable) selectEl.refreshSearchable();
        return;
    }
    selectEl.dataset.searchableInit = "true";

    // Ẩn select gốc nhưng giữ trong DOM để form submit & serialize
    selectEl.style.display = "none";

    const wrapper = document.createElement("div");
    wrapper.className = "dt-search-wrapper";

    const inputWrap = document.createElement("div");
    inputWrap.className = "dt-search-input-wrap";

    const searchIcon = document.createElement("i");
    searchIcon.className = "fa-solid fa-magnifying-glass dt-search-icon";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "dt-search-input";
    input.autocomplete = "off";
    input.spellcheck = false;

    // Placeholder
    const firstOpt = selectEl.querySelector("option");
    const placeholderText = customPlaceholder || selectEl.getAttribute("data-placeholder") || (firstOpt && firstOpt.value === "" ? firstOpt.textContent : "Gõ để tìm kiếm...");
    input.placeholder = placeholderText;

    // Nút xóa (clear)
    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "dt-search-clear";
    clearBtn.innerHTML = "&times;";
    clearBtn.title = "Xóa lựa chọn";
    clearBtn.style.display = "none";

    // Mũi tên chỉ xuống
    const arrowIcon = document.createElement("i");
    arrowIcon.className = "fa-solid fa-chevron-down dt-search-arrow";

    inputWrap.appendChild(searchIcon);
    inputWrap.appendChild(input);
    inputWrap.appendChild(clearBtn);
    inputWrap.appendChild(arrowIcon);

    // Dropdown danh sách kết quả
    const dropdown = document.createElement("div");
    dropdown.className = "dt-search-dropdown";

    wrapper.appendChild(inputWrap);
    wrapper.appendChild(dropdown);
    selectEl.parentNode.insertBefore(wrapper, selectEl.nextSibling);

    let activeIndex = -1;

    // Xây dựng danh sách các option từ select gốc
    function buildOptions() {
        dropdown.innerHTML = "";
        const options = Array.from(selectEl.options);
        let hasValid = false;

        options.forEach(opt => {
            if (opt.value === "") return; // Bỏ qua placeholder rỗng
            hasValid = true;
            const item = document.createElement("div");
            item.className = "dt-search-item" + (opt.selected ? " is-selected" : "");
            item.dataset.value = opt.value;
            item.textContent = opt.textContent.trim();

            item.addEventListener("mousedown", (e) => {
                e.preventDefault();
                selectOption(opt.value, opt.textContent.trim());
            });
            dropdown.appendChild(item);
        });

        const empty = document.createElement("div");
        empty.className = "dt-search-empty";
        empty.textContent = "Không tìm thấy kết quả phù hợp";
        empty.style.display = hasValid ? "none" : "block";
        dropdown.appendChild(empty);

        syncDisplayFromSelect();
    }

    // Đồng bộ giá trị hiển thị từ select sang ô input (chỉ gọi khi init hoặc sau khi đóng)
    function syncDisplayFromSelect() {
        const selectedOpt = selectEl.options[selectEl.selectedIndex];
        if (selectedOpt && selectedOpt.value !== "") {
            input.value = selectedOpt.textContent.trim();
            clearBtn.style.display = "block";
            wrapper.classList.add("has-value");
        } else {
            input.value = "";
            clearBtn.style.display = "none";
            wrapper.classList.remove("has-value");
        }

        if (selectEl.disabled) {
            input.disabled = true;
            wrapper.classList.add("is-disabled");
        } else {
            input.disabled = false;
            wrapper.classList.remove("is-disabled");
        }
    }

    // Lọc các item theo chuỗi gõ từ bàn phím
    function filterOptions(query) {
        const q = (query || "").toLowerCase().trim();
        const items = dropdown.querySelectorAll(".dt-search-item");
        let matchCount = 0;
        activeIndex = -1;

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.classList.remove("is-focused");
            if (!q || text.includes(q)) {
                item.style.display = "flex";
                matchCount++;
            } else {
                item.style.display = "none";
            }
        });

        const empty = dropdown.querySelector(".dt-search-empty");
        if (empty) {
            empty.style.display = matchCount === 0 ? "block" : "none";
        }
    }

    function openDropdown() {
        if (selectEl.disabled) return;
        dropdown.classList.add("show");
        wrapper.classList.add("is-open");
    }

    function closeDropdown() {
        dropdown.classList.remove("show");
        wrapper.classList.remove("is-open");
        activeIndex = -1;
        syncDisplayFromSelect();
    }

    function selectOption(val, text) {
        selectEl.value = val;
        input.value = text;
        clearBtn.style.display = "block";
        wrapper.classList.add("has-value");
        dropdown.classList.remove("show");
        wrapper.classList.remove("is-open");

        // Đánh dấu is-selected cho item được chọn
        dropdown.querySelectorAll(".dt-search-item").forEach(item => {
            if (item.dataset.value === val) {
                item.classList.add("is-selected");
            } else {
                item.classList.remove("is-selected");
            }
        });

        // Kích hoạt sự kiện change trên thẻ select gốc
        const event = new Event("change", { bubbles: true });
        selectEl.dispatchEvent(event);
    }

    function clearSelection() {
        selectEl.value = "";
        input.value = "";
        clearBtn.style.display = "none";
        wrapper.classList.remove("has-value");
        dropdown.querySelectorAll(".dt-search-item").forEach(item => item.classList.remove("is-selected"));
        filterOptions("");
        openDropdown();

        const event = new Event("change", { bubbles: true });
        selectEl.dispatchEvent(event);
        input.focus();
    }

    // --- SỰ KIỆN GÕ PHÍM TRỰC TIẾP TỪ BÀN PHÍM ---
    input.addEventListener("focus", () => {
        openDropdown();
        // Khi bấm vào ô, bôi đen toàn bộ để người dùng gõ phím là tìm kiếm được ngay
        setTimeout(() => input.select(), 50);
        filterOptions("");
    });

    input.addEventListener("input", (e) => {
        // KHÔNG BAO GIỜ ghi đè input.value khi người dùng đang gõ
        openDropdown();
        clearBtn.style.display = input.value ? "block" : "none";
        filterOptions(input.value);
    });

    input.addEventListener("keydown", (e) => {
        const visibleItems = Array.from(dropdown.querySelectorAll(".dt-search-item")).filter(it => it.style.display !== "none");
        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (!dropdown.classList.contains("show")) {
                openDropdown();
                return;
            }
            if (visibleItems.length > 0) {
                activeIndex = (activeIndex + 1) % visibleItems.length;
                visibleItems.forEach((it, idx) => {
                    it.classList.toggle("is-focused", idx === activeIndex);
                    if (idx === activeIndex) it.scrollIntoView({ block: "nearest" });
                });
            }
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (visibleItems.length > 0) {
                activeIndex = (activeIndex - 1 + visibleItems.length) % visibleItems.length;
                visibleItems.forEach((it, idx) => {
                    it.classList.toggle("is-focused", idx === activeIndex);
                    if (idx === activeIndex) it.scrollIntoView({ block: "nearest" });
                });
            }
        } else if (e.key === "Enter") {
            if (dropdown.classList.contains("show") && activeIndex >= 0 && visibleItems[activeIndex]) {
                e.preventDefault();
                const target = visibleItems[activeIndex];
                selectOption(target.dataset.value, target.textContent.trim());
            } else if (dropdown.classList.contains("show") && visibleItems.length === 1) {
                e.preventDefault();
                selectOption(visibleItems[0].dataset.value, visibleItems[0].textContent.trim());
            }
        } else if (e.key === "Escape") {
            closeDropdown();
        }
    });

    arrowIcon.addEventListener("click", (e) => {
        e.stopPropagation();
        if (dropdown.classList.contains("show")) {
            closeDropdown();
        } else {
            input.focus();
            openDropdown();
            filterOptions("");
        }
    });

    clearBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        clearSelection();
    });

    document.addEventListener("click", (e) => {
        if (!wrapper.contains(e.target)) {
            closeDropdown();
        }
    });

    // Hàm gọi khi danh sách options của select gốc được cập nhật (ví dụ qua AJAX)
    selectEl.refreshSearchable = function () {
        buildOptions();
    };

    buildOptions();
    return wrapper;
}
