//input_control.js

export class CommandInputHandler {
    constructor(suggestions, defaultText, $msg_inputer, $cmd_dropdownMenu, $ai_icon, prompt_variable_str, cssClasses, sentenceCompletionFunc) {
        this.sentenceCompletionFunc = sentenceCompletionFunc;
        this.icon_default_svg = `<svg width="30px" height="30px" viewBox="0 0 24 24" data-name="025_SCIENCE" id="_025_SCIENCE" xmlns="http://www.w3.org/2000/svg">
        <defs>
        <style>
                .cls-1 {
                    fill: #ffffff;
                }
            </style>
        </defs>
        <path class="cls-1"
            d="M16,13H8a3,3,0,0,1-3-3V6A3,3,0,0,1,8,3h8a3,3,0,0,1,3,3v4A3,3,0,0,1,16,13ZM8,5A1,1,0,0,0,7,6v4a1,1,0,0,0,1,1h8a1,1,0,0,0,1-1V6a1,1,0,0,0-1-1Z" />
        <path class="cls-1"
            d="M10,9a1.05,1.05,0,0,1-.71-.29A1,1,0,0,1,10.19,7a.6.6,0,0,1,.19.06.56.56,0,0,1,.17.09l.16.12A1,1,0,0,1,10,9Z" />
        <path class="cls-1"
            d="M14,9a1,1,0,0,1-.71-1.71,1,1,0,0,1,1.42,1.42,1,1,0,0,1-.16.12.56.56,0,0,1-.17.09.6.6,0,0,1-.19.06Z" />
        <path class="cls-1" d="M12,4a1,1,0,0,1-1-1V2a1,1,0,0,1,2,0V3A1,1,0,0,1,12,4Z" />
        <path class="cls-1" d="M9,22a1,1,0,0,1-1-1V18a1,1,0,0,1,2,0v3A1,1,0,0,1,9,22Z" />
        <path class="cls-1" d="M15,22a1,1,0,0,1-1-1V18a1,1,0,0,1,2,0v3A1,1,0,0,1,15,22Z" />
        <path class="cls-1"
            d="M15,19H9a1,1,0,0,1-1-1V12a1,1,0,0,1,1-1h6a1,1,0,0,1,1,1v6A1,1,0,0,1,15,19Zm-5-2h4V13H10Z" />
        <path class="cls-1"
            d="M5,17a1,1,0,0,1-.89-.55,1,1,0,0,1,.44-1.34l4-2a1,1,0,1,1,.9,1.78l-4,2A.93.93,0,0,1,5,17Z" />
        <path class="cls-1"
            d="M19,17a.93.93,0,0,1-.45-.11l-4-2a1,1,0,1,1,.9-1.78l4,2a1,1,0,0,1,.44,1.34A1,1,0,0,1,19,17Z" />
    </svg>`;
        this.suggestions = suggestions;
        this.defaultText = defaultText;
        this.$msg_inputer = $msg_inputer;
        this.$cmd_dropdownMenu = $cmd_dropdownMenu;
        this.$ai_icon = $ai_icon;
        this.prompt_variable_str = prompt_variable_str;
        this.cssClasses = cssClasses;

        // this.filteredSuggestions = this.suggestions.map(suggestion =>
        //     `<li class='${this.cssClasses.cmdItems}' data-desc='${suggestion.cmd.replace('[contents]', this.prompt_variable_str)}' data-svg='${suggestion.svg}' data-prompt='${suggestion.prompt.replace('[contents]', this.prompt_variable_str)}'>
        //         <span class='${this.cssClasses.itemName}'>${suggestion.name}</span>
        //         <span class='${this.cssClasses.sugDesc}'>${suggestion.descript}</span>
        //     </li>`
        // ).join('');
        this.filteredSuggestions = [];
        $.each(this.suggestions, (key, value) => {
            let prompt = this.suggestions[key].prompt.replace('[contents]', this.prompt_variable_str)
            let sugDesc = this.suggestions[key].descript.replace('[contents]', this.prompt_variable_str)
            let li_html = `<li class='${this.cssClasses.cmdItems}' data-desc='${this.suggestions[key].cmd}' data-svg='' data-prompt='${prompt}'>
                        <span class='${this.cssClasses.itemName}'><div>${this.suggestions[key].svg}</div><div>${this.suggestions[key].name}</div></span>
                        <span class='${this.cssClasses.sugDesc}'>${sugDesc}</span>
                    </li>`
            this.filteredSuggestions.push(li_html);
        });
        this.filteredSuggestions.reverse();
        this.filteredSuggestions = this.filteredSuggestions.join('');
        this.$msg_inputer.val(this.defaultText);
        this.selectedItemIndex = -1;
        this.command_flag = "cmd_normal";
        this.prompt_flag = null;
        this.sentenceTimer = null;
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
                this.$ai_icon.html(this.icon_default_svg);
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
            if (this.$cmd_dropdownMenu.is(":visible")) {
                // dropdownMenu key events
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
            } else {
                // inputer key events
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (this.$msg_inputer.val() !== '' && this.$msg_inputer.val() !== this.defaultText && this.$msg_inputer.val() !== this.prompt_variable_str) {
                        if (this.sentenceTimer) {
                            clearTimeout(this.sentenceTimer);
                            this.sentenceTimer = null;
                        }
                        if (this.$msg_inputer[0].selectionStart === this.$msg_inputer[0].selectionEnd) {
                            // 光标没有选中任何文本
                            this.triggerSendMsgEvent();
                            //reset after trigger sendmsg event
                            this.resetAll();
                            this.autoExpand(this.$msg_inputer[0]);

                        }

                    }
                }
                if (e.key === "Backspace" || e.key === "Delete") {
                    if (this.$msg_inputer.val().length <= 0) {
                        this.resetAll();
                    }
                }
                if (e.key === "Tab") {
                    e.preventDefault();
                    if (this.sentenceTimer) {
                        clearTimeout(this.sentenceTimer);
                        this.sentenceTimer = null;
                    }
                    this.sentenceCompletionFunc();
                }
                if (e.key === "Escape") {
                    e.preventDefault();
                    this.$msg_inputer[0].selectionStart = this.$msg_inputer[0].selectionEnd = this.$msg_inputer.val().length;
                }
            }
        });

        this.$msg_inputer.on('keyup', (e) => {
            if (e.key === " ") {
                let value = this.$msg_inputer.val();
                if (/ $/.test(value)) {
                    // If the sentence ends with a space, start the timer for sentence completion
                    if (this.sentenceTimer) {
                        clearTimeout(this.sentenceTimer);
                    }
                    this.sentenceTimer = setTimeout(() => {
                        this.sentenceCompletionFunc();
                    }, 4000);
                }
            } else if (this.sentenceTimer) {
                clearTimeout(this.sentenceTimer);
                this.sentenceTimer = null;
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
        this.$ai_icon.html(this.icon_default_svg).hide();
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
        let svg_icon = this.suggestions[this.command_flag].svg;
        this.$msg_inputer.val(this.prompt_variable_str);
        let startIndex = 0;
        let endIndex = this.prompt_variable_str.length;
        this.$msg_inputer[0].setSelectionRange(startIndex, endIndex);
        this.$msg_inputer.focus();
        $liItem_select.siblings().find(`.${this.cssClasses.sugDesc}`).hide();
        this.$cmd_dropdownMenu.hide();
        this.$ai_icon.html(svg_icon);
        console.log(`current cmd is ${this.command_flag}`);
    }

    changeItem(index) {
        let $liItem_select = this.$cmd_dropdownMenu.find(`li.${this.cssClasses.cmdItems}`).eq(index);
        $liItem_select.addClass(this.cssClasses.highlight);
        $liItem_select.siblings().removeClass(this.cssClasses.highlight);
        $liItem_select.find(`.${this.cssClasses.sugDesc}`).show();
        $liItem_select.siblings().find(`.${this.cssClasses.sugDesc}`).hide();
        $liItem_select.find('svg').addClass(this.cssClasses.highlight_svg);
        $liItem_select.siblings().find('svg').removeClass(this.cssClasses.highlight_svg);
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

// // 导出类
// export default CommandInputHandler;