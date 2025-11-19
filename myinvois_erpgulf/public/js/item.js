function make_searchable_dropdown(frm, fieldname) {
    setTimeout(() => {
        if (!frm || !frm.fields_dict || !frm.fields_dict[fieldname]) return;

        const field = frm.fields_dict[fieldname];
        const $field = field.$wrapper;
        const $select = field.$input;

        if (!$select || $field.hasClass('searchable-enhanced')) return;

        $field.addClass('searchable-enhanced');

        const $controlContainer = $field.find('.control-input-wrapper');

        const options = [];
        $select.find('option').each(function () {
            if ($(this).val()) {
                options.push({
                    value: $(this).val(),
                    text: $(this).text()
                });
            }
        });

        const $customContainer = $(`
            <div class="custom-dropdown-container" style="position: relative; width: 100%;">
                <input type="text" class="form-control custom-dropdown-input" 
                       placeholder="Search ${field.df.label || fieldname}..." 
                       style="width: 100%; display: block; position: relative; z-index: 1;">
                <div class="custom-dropdown-list" 
                     style="position: absolute; top: 100%; left: 0; width: 100%; 
                            max-height: 200px; overflow-y: auto; z-index: 1001;
                            background: white; border: 1px solid #d1d8dd; 
                            border-radius: 0 0 4px 4px; display: none;"></div>
            </div>
        `);

        const $searchInput = $customContainer.find('.custom-dropdown-input');
        const $dropdownList = $customContainer.find('.custom-dropdown-list');

        $select.hide();
        $controlContainer.append($customContainer);

        function updateDropdown(searchText) {
            $dropdownList.empty();

            const filtered = options.filter(opt =>
                opt.text.toLowerCase().includes(searchText.toLowerCase()) || !searchText
            );

            filtered.forEach(opt => {
                // Removed the border-bottom style
                const $option = $(`
                    <div class="custom-dropdown-option" 
                         style="padding: 8px; cursor: pointer;">
                        ${opt.text}
                    </div>
                `);

                // Add hover effect without borders
                $option.hover(
                    function () { $(this).css('background-color', '#f7fafc'); },
                    function () { $(this).css('background-color', ''); }
                );

                $option.data('value', opt.value);
                $dropdownList.append($option);
            });

            if (filtered.length > 0) {
                $dropdownList.show();
            } else {
                $dropdownList.hide();
            }
        }

        $searchInput.on('focus', function () {
            updateDropdown($searchInput.val());
        });

        $searchInput.on('input', function () {
            updateDropdown($(this).val());
        });

        $dropdownList.on('click', '.custom-dropdown-option', function () {
            const value = $(this).data('value');
            const text = $(this).text().trim();

            $searchInput.val(text);
            $select.val(value).trigger('change');
            $dropdownList.hide();
        });

        $(document).on('click', function (e) {
            if (!$(e.target).closest($customContainer).length) {
                $dropdownList.hide();
            }
        });

        if ($select.val()) {
            const selectedOption = options.find(opt => opt.value === $select.val());
            if (selectedOption) {
                $searchInput.val(selectedOption.text);
            }
        }

        $select.on('change', function () {
            const val = $(this).val();
            const selectedOption = options.find(opt => opt.value === val);
            if (selectedOption) {
                $searchInput.val(selectedOption.text);
            }
        });
    }, 500);
};

frappe.ui.form.on('Item', {
    refresh: function(frm) {
        make_searchable_dropdown(frm, 'custom_item_classification_code');
    }
});

