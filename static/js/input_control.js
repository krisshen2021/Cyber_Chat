class CommandInputHandler {
    constructor(icons, suggestions, defaultText, $msg_inputer, $cmd_dropdownMenu, $ai_icon, prompt_variable_str, cssClasses) {
        this.icons = icons;
        this.suggestions = suggestions;
        this.defaultText = defaultText;
        this.$msg_inputer = $msg_inputer;
        this.$cmd_dropdownMenu = $cmd_dropdownMenu;
        this.$ai_icon = $ai_icon;
        this.prompt_variable_str = prompt_variable_str;
        this.cssClasses = cssClasses;

        this.filteredSuggestions = this.suggestions.map(suggestion =>
            `<li class='${this.cssClasses.cmdItems}' data-desc='${suggestion.cmd.replace('[contents]', this.prompt_variable_str)}' data-svg='${suggestion.svg}' data-prompt='${suggestion.prompt.replace('[contents]', this.prompt_variable_str)}'>
                <span class='${this.cssClasses.itemName}'>${suggestion.name}</span>
                <span class='${this.cssClasses.sugDesc}'>${suggestion.descript}</span>
            </li>`
        ).join('');
        this.$msg_inputer.val(this.defaultText);
        this.selectedItemIndex = -1;
        this.command_flag = "cmd_normal";
        this.prompt_flag = null;
        this.initializeEventBindings();
    }

    initializeEventBindings() {
        this.$msg_inputer.on("focus", () => {
            if (this.$msg_inputer.val() === this.defaultText) {
                this.$msg_inputer.val("").addClass(this.cssClasses.inputText);
            }
        });

        this.$msg_inputer.on("blur", () => {
            if (this.$msg_inputer.val() === "") {
                this.$msg_inputer.val(this.defaultText).removeClass(this.cssClasses.inputText);
            }
        });

        this.$msg_inputer.on('input', () => {
            let value = this.$msg_inputer.val();
            if (/^\/$/.test(value)) {
                this.$cmd_dropdownMenu.html(this.filteredSuggestions).css("display", "flex");
                this.setItemMenuPos();
                this.command_flag = "cmd_normal";
                this.prompt_flag = null;
                this.$ai_icon.html(this.icons.default);
                this.$ai_icon.show();
                this.selectedItemIndex = -1;
            } else {
                this.$cmd_dropdownMenu.hide();
                if (this.command_flag === "cmd_normal") {
                    this.$ai_icon.hide();
                }
            }
            this.autoExpand(this.$msg_inputer[0]);
            // console.log(`current cmd is ${this.command_flag}`);
        });

        this.$msg_inputer.on('keydown', (e) => {
            let $items = this.$cmd_dropdownMenu.find(`li.${this.cssClasses.cmdItems}`);
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!this.$cmd_dropdownMenu.is(":visible") && this.$msg_inputer.val() !== '' && this.$msg_inputer.val() !== this.defaultText && this.$msg_inputer.val() !== this.prompt_variable_str) {
                    this.triggerSendMsgEvent();
                    //reset after trigger sendmsg event
                    this.resetAll();
                    this.autoExpand(this.$msg_inputer[0]);
                }
            }
            if (this.$cmd_dropdownMenu.is(":visible")) {
                if (e.key === 'Escape') {
                    this.resetAll();
                }
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.selectedItemIndex = (this.selectedItemIndex + 1) % $items.length;
                    this.changeItem(this.selectedItemIndex);
                    this.setItemMenuPos();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.selectedItemIndex = (this.selectedItemIndex - 1 + $items.length) % $items.length;
                    this.changeItem(this.selectedItemIndex);
                    this.setItemMenuPos();
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (this.selectedItemIndex >= 0) {
                        this.selectItem(this.selectedItemIndex);
                        this.autoExpand(this.$msg_inputer[0]);
                    }
                }
            }
            if (e.key === "Backspace" || e.key === "Delete") {
                if (this.$msg_inputer.val().length <= 0) {
                    this.resetAll();
                }
            }
        });

        this.$cmd_dropdownMenu.on('click', `li.${this.cssClasses.cmdItems}`, () => {
            this.selectItem(this.selectedItemIndex);
        });

        this.$cmd_dropdownMenu.on('mouseover', `li.${this.cssClasses.cmdItems}`, (event) => {
            this.changeItem($(event.currentTarget).index());
        });

        // Add this click event binding to the document
        $(document).on('click', (e) => {
            if (!$(e.target).closest(this.$msg_inputer).length && !$(e.target).closest(this.$cmd_dropdownMenu).length && this.$cmd_dropdownMenu.is(":visible")) {
                this.resetAll();
            };
        });

    }

    resetAll() {
        this.selectedItemIndex = -1;
        this.$cmd_dropdownMenu.hide();
        this.$msg_inputer.val("");
        this.command_flag = "cmd_normal";
        this.prompt_flag = null;
        this.$ai_icon.html(this.icons.default).hide();
    }
    autoExpand(textarea) {
        setTimeout(() => {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }, 0);
    }
    setItemMenuPos() {
        let posX = 0;
        let posY = 0 - this.$cmd_dropdownMenu.outerHeight(true);
        this.$cmd_dropdownMenu.css(
            {
                position: 'absolute',
                left: posX + 'px',
                top: posY + 'px'
            }
        );
    }

    selectItem(index) {
        let $liItem_select = this.$cmd_dropdownMenu.find(`li.${this.cssClasses.cmdItems}`).eq(index);
        this.command_flag = $liItem_select.data('desc');
        this.prompt_flag = $liItem_select.data('prompt');
        let svg_icon = $liItem_select.data('svg');
        this.$msg_inputer.val(this.prompt_variable_str);
        let startIndex = 0;
        let endIndex = this.prompt_variable_str.length;
        this.$msg_inputer[0].setSelectionRange(startIndex, endIndex);
        this.$msg_inputer.focus();
        $liItem_select.siblings().find(`.${this.cssClasses.sugDesc}`).hide();
        this.$cmd_dropdownMenu.hide();
        this.$ai_icon.html(svg_icon);
    }

    changeItem(index) {
        let $liItem_select = this.$cmd_dropdownMenu.find(`li.${this.cssClasses.cmdItems}`).eq(index);
        $liItem_select.addClass(this.cssClasses.highlight);
        $liItem_select.siblings().removeClass(this.cssClasses.highlight);
        $liItem_select.find(`.${this.cssClasses.sugDesc}`).show();
        $liItem_select.siblings().find(`.${this.cssClasses.sugDesc}`).hide();
        this.selectedItemIndex = $liItem_select.index();
    }

    triggerSendMsgEvent() {
        // Custom event using jQuery's event system
        let data = {
            command_flag: this.command_flag,
            prompt_flag: this.prompt_flag,
            msg: this.$msg_inputer.val()
        }
        const event = $.Event('SendMsg', data);
        this.$msg_inputer.trigger(event);
    }
    triggerEnterEvent() {
        this.$msg_inputer.trigger(jQuery.Event('keydown', { key: 'Enter', shiftKey: false }));
    }
}

// 导出类
export default CommandInputHandler;