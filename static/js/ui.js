// require jquery
export class SwitchUI {
    constructor(options) {
        this.element = $(options.element);
        this.width = options.width;
        this.height = options.height;
        this.isOn = options.value || false;
        this.onColor = options.onColor;
        this.offColor = options.offColor;
        this.init();
    }
    init() {
        this.element.attr('data-value', this.isOn);
        this.element.css({
            'width': this.width + 'px',
            'height': this.height + 'px',
            'border-radius': this.height / 2 + 'px',
            'cursor': 'pointer',
            'position': 'relative',
            'overflow': 'hidden'
        });

        this.roundButton = $('<div>').css({
            'width': this.height * 0.8 + 'px',
            'height': this.height * 0.8 + 'px',
            'border-radius': '50%',
            'background-color': 'white',
            'position': 'absolute',
            'top': '50%',
            'left': this.height * 0.1 + 'px',
            'transform': 'translate(0, -50%)',
            'transition': 'left 0.3s'
        });

        if (this.isOn) {
            this.element.css({
                'background-color': this.onColor,
            });
            this.roundButton.css('left', 'calc(100% - ' + this.height * 0.9 + 'px)');
        } else {
            this.element.css({
                'background-color': this.offColor,
            });
            this.roundButton.css('left', this.height * 0.1 + 'px');
        }

        this.element.append(this.roundButton);
        this.element.on('click', () => {
            this.toggle();
        });
    }
    toggle() {
        this.isOn = !this.isOn;
        if (this.isOn) {
            this.element.css('background-color', this.onColor);
            this.roundButton.css('left', 'calc(100% - ' + this.height * 0.9 + 'px)');
            this.element.attr('data-value', this.isOn);
        } else {
            this.element.css('background-color', this.offColor);
            this.roundButton.css('left', this.height * 0.1 + 'px');
            this.element.attr('data-value', this.isOn);
        }
        this.element.trigger('change', [this.isOn]);
    }
    getValue() {
        return this.isOn;
    }
}

export class VolumeKnob {
    constructor(options) {
        this.element = $(options.element);
        this.minValue = options.minValue || 0;
        this.maxValue = options.maxValue || 1;
        this.stepValue = options.stepValue || 0.01;
        this.width = options.width || 100;
        this.height = options.height || 100;
        this.backgroundImage = options.backgroundImage || '';
        this.backgroundColor = options.backgroundColor || 'transparent';
        this.knobHandlerColor = options.knobHandlerColor || '#ffffff';
        this.audioElement = options.audioElement;
        this.initialVolume = options.initialVolume !== undefined ? options.initialVolume : 0.5;
        this.isDragging = false;
        this.startAngle = 0;
        this.mouseLocation = [0, 0];
        this.init();
    }

    init() {
        this.element.css({
            'cursor': 'pointer',
            'user-select': 'none',
            'width': `${this.width}px`,
            'height': `${this.height}px`,
            'background-image': `url(${this.backgroundImage})`,
            'background-size': 'cover',
            'background-position': 'center',
            'background-repeat': 'no-repeat',
            'background-color': this.backgroundColor,
            'border-radius': '50%',
            'position': 'relative',
        });

        // Create the knob handler
        this.knobHandler = $('<div>').css({
            'position': 'absolute',
            'top': '10%',
            'left': '50%',
            'transform': 'translate(-50%, 0%)',
            'width': this.width * 0.15,
            'height': this.height * 0.25,
            'background-color': this.knobHandlerColor,
            'border-radius': '40%',
        });

        this.element.append(this.knobHandler);

        this.element.on('mousedown', this.onMouseDown.bind(this));
        $(document).on('mousemove', this.onMouseMove.bind(this));
        $(document).on('mouseup', this.onMouseUp.bind(this));

        if (this.audioElement) {
            this.audioElement.volume = this.initialVolume;
            this.value = this.audioElement.volume;
            this.angle = this.valueToAngle(this.value);
        } else {
            this.value = this.minValue;
            this.angle = -135;
        }

        this.updateKnob();
    }
    toggleStatus() {
        //toggle play/pause
        if (this.audioElement.paused) {
            this.audioElement.play();
            this.element.css({
                'background-color': this.backgroundColor,
                'transition': 'background-color 0.5s ease-in-out'
            });
            console.log("background music is playing");
        } else {
            this.audioElement.pause();
            this.element.css({
                'background-color': 'rgba(111, 111, 111, 0.5)',
                'transition': 'background-color 0.5s ease-in-out'
            });
            console.log("background music is paused");
        }
    }
    onMouseDown(e) {
        this.isDragging = true;
        const rect = this.element[0].getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        this.startAngle = this.calculateAngle(e.clientX, e.clientY, centerX, centerY);
        this.mouseLocation = [e.clientX, e.clientY];
    }

    onMouseMove(e) {
        if (!this.isDragging) return;

        const rect = this.element[0].getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const currentAngle = this.calculateAngle(e.clientX, e.clientY, centerX, centerY);

        let angleDiff = currentAngle - this.startAngle;
        if (angleDiff > 180) angleDiff -= 360;
        if (angleDiff < -180) angleDiff += 360;

        this.angle += angleDiff;
        this.angle = Math.max(-135, Math.min(135, this.angle));

        this.startAngle = currentAngle;
        this.updateKnob();
    }

    onMouseUp(e) {
        this.isDragging = false;
        if (this.mouseLocation[0] === e.clientX && this.mouseLocation[1] === e.clientY) {
            this.toggleStatus();
        }
    }

    calculateAngle(x, y, centerX, centerY) {
        const dx = x - centerX;
        const dy = y - centerY;
        let angle = Math.atan2(dy, dx) * 180 / Math.PI;
        angle = (angle + 360) % 360;
        return angle;
    }

    updateKnob() {
        this.element.css('transform', `rotate(${this.angle}deg)`);

        const range = this.maxValue - this.minValue;
        const angleRange = 270; // -135 to 135 degrees
        this.value = this.minValue + (this.angle + 135) / angleRange * range;
        this.value = Math.round(this.value / this.stepValue) * this.stepValue;
        this.value = Math.max(this.minValue, Math.min(this.maxValue, this.value));

        if (this.audioElement) {
            this.audioElement.volume = this.value;
        }

        this.element.trigger('change', [this.value]);
    }

    valueToAngle(value) {
        const range = this.maxValue - this.minValue;
        const angleRange = 270; // -135 to 135 degrees
        return (value - this.minValue) / range * angleRange - 135;
    }

    getValue() {
        return this.value;
    }
}

export class SelectorUI {
    // 下拉选择器, 默认为语言选择器，可以自定义列表
    constructor(options) {
        this.element = $(options.element);
        this.width = options.width || 100;
        this.height = options.height || 30;
        this.selectorColor = options.selectorColor || '#ffffff';
        this.selectorTextColor = options.selectorTextColor || '#361c4c';
        this.selectorHoverColor = options.selectorHoverColor || '#361c4c';
        this.selectorTextHoverColor = options.selectorTextHoverColor || '#ffffff';
        this.itemColor = options.itemColor || '#ffffff';
        this.itemHoverColor = options.itemHoverColor || '#361c4c';
        this.itemTextColor = options.itemTextColor || '#361c4c';
        this.itemTextHoverColor = options.itemTextHoverColor || '#ffffff';
        this.isOpen = false;
        this.itemList = options.itemList || [];
        this.init();
    }
    init() {
        // 如果列表为空，则使用默认列表
        if (this.itemList.length === 0) {
            this.itemList = [
                {
                    name: 'English',
                    value: 'English'
                },
                {
                    name: '简体中文',
                    value: 'Simplified Chinese'
                },
                {
                    name: '繁體中文',
                    value: 'Traditional Chinese'
                },
                {
                    name: '日本語',
                    value: 'Japanese'
                },
                {
                    name: 'Français',
                    value: 'French'
                },
                {
                    name: 'Deutsch',
                    value: 'German'
                },
                {
                    name: 'Español',
                    value: 'Spanish'
                },
                {
                    name: '한국어',
                    value: 'Korean'
                },
                {
                    name: 'Português',
                    value: 'Portuguese'
                },
                {
                    name: 'Italiano',
                    value: 'Italian'
                },
                {
                    name: 'Русский',
                    value: 'Russian'
                },
                {
                    name: 'Türkçe',
                    value: 'Turkish'
                },
                {
                    name: 'Polski',
                    value: 'Polish'
                },
            ];
        }
        this.currentItem = this.itemList[0];
        this.currentItemIndex = 0;
        this.element.attr('data-value', this.currentItem.value);
        this.clickArea = $('<div>').css({
            'cursor': 'pointer',
            'user-select': 'none',
            'padding': '0 10px',
            'border-radius': this.height / 2 + 'px',
            'background-color': this.selectorColor,
            'transition': 'background-color 0.3s ease-in-out',
            'color': this.selectorTextColor,
            'width': 'max-content',
            'height': this.height + 'px',
            'font-size': this.height / 2 + 'px',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'center',
        });
        this.clickArea.text(this.currentItem.name);
        this.element.css({
            'width': 'max-content',
            'height': this.height + 'px',
            'font-size': this.height / 2 + 'px',
            'font-weight': 'bold',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            'position': 'relative',
        });
        this.itemListContainer = $('<div>').css({
            'position': 'absolute',
            'top': (this.height + 10) + 'px',
            'left': '0',
            'width': 'max-content',
            'max-height': '300px',
            'overflow-y': 'auto',
            'border-radius': '5px',
            'background-color': this.itemColor,
            'display': 'none',
            'flex-direction': 'column',
            'align-items': 'center',
            'justify-content': 'flex-start',
            'padding': '10px',
            'gap': '5px',
            'box-shadow': '0 0 10px 0 rgba(0, 0, 0, 0.5)',
            'scrollbar-width': 'thin',
            'scrollbar-color': '#361c4c transparent',
        })

        this.itemList.forEach(item => {
            const List_item = $('<div>').css({
                'cursor': 'pointer',
                'border-radius': '3px',
                'color': this.itemTextColor,
                'width': '100%',
                'min-height': this.height + 'px',
                'padding': '0 10px',
                'display': 'flex',
                'align-items': 'center',
                'justify-content': 'center',
                'transition': 'background-color 0.3s ease-in-out'
            });
            List_item.text(item.name);
            List_item.attr('data-value', item.value);
            this.itemListContainer.append(List_item);
        });
        this.element.append(this.clickArea);
        this.element.append(this.itemListContainer);
        //高亮当前项
        this.itemListContainer.find('div[data-value="' + this.currentItem.value + '"]').css('background-color', this.itemHoverColor);
        this.itemListContainer.find('div[data-value="' + this.currentItem.value + '"]').css('color', this.itemTextHoverColor);
        this.clickArea.hover(() => {
            this.clickArea.css('background-color', this.selectorHoverColor);
            this.clickArea.css('color', this.selectorTextHoverColor);
        }, () => {
            this.clickArea.css('background-color', this.selectorColor);
            this.clickArea.css('color', this.selectorTextColor);
        });
        this.clickArea.on('click', () => {
            this.toggleItemList();
        });
        this.itemListContainer.on('click', 'div', (e) => {
            const clickedValue = $(e.target).attr('data-value');
            const clickedItem = this.itemList.find(item => item.value === clickedValue);
            if (clickedItem) {
                this.selectItem(clickedItem);
                this.toggleItemList();
            }
        });
        this.itemListContainer.on('mouseenter', 'div', (e) => {
            $(e.target).css('background-color', this.itemHoverColor);
            $(e.target).css('color', this.itemTextHoverColor);
        }).on('mouseleave', 'div', (e) => {
            $(e.target).css('background-color', this.itemColor);
            $(e.target).css('color', this.itemTextColor);
        });
        $(document).on('click', (e) => {
            if (!this.element.is(e.target) && this.element.has(e.target).length === 0) {
                this.hideItemList();
            }
        });
    }
    selectItem(item) {
        this.currentItem = item;
        this.currentItemIndex = this.itemList.indexOf(item);
        this.updateItemDisplay();
    }
    updateItemDisplay() {
        this.clickArea.text(this.currentItem.name);
        this.element.attr('data-value', this.currentItem.value);
        //trigger a change event
        this.element.trigger('change', [this.currentItem]);
    }
    toggleItemList() {
        if (this.isOpen) {
            this.itemListContainer.css('display', 'none');
            this.isOpen = false;
        } else {
            this.itemListContainer.css('display', 'flex');
            this.isOpen = true;
            this.itemListContainer.find('div').css('background-color', this.itemColor);
            this.itemListContainer.find('div').css('color', this.itemTextColor);
            this.itemListContainer.find('div[data-value="' + this.currentItem.value + '"]').css('background-color', this.itemHoverColor);
            this.itemListContainer.find('div[data-value="' + this.currentItem.value + '"]').css('color', this.itemTextHoverColor);
            
        }
    }
    getValue() {
        return this.currentItem.value;
    }
    hideItemList() {
        this.itemListContainer.css('display', 'none');
        this.isOpen = false;
    }
    setItem(value) {
        const item = this.itemList.find(item => item.value === value);
        if (item) {
            this.currentItem = item;
            this.updateItemDisplay();
            this.element.attr('data-value', this.currentItem.value);
        } else {
            console.warn(`Item with value "${value}" not found in the item list.`);
        }
    }
    updateListItems(itemList) {
        // 更新列表，外部调用
        this.itemList = itemList;

        // 保存当前选中项的值
        const currentValue = this.currentItem.value;

        // 更新列表容器
        this.itemListContainer.empty();
        this.itemList.forEach(item => {
            const listItem = this.createListItem(item);
            this.itemListContainer.append(listItem);
        });

        // 尝试恢复之前的选择，如果不存在则选择第一项
        // const newSelectedItem = this.itemList.find(item => item.value === currentValue) || this.itemList[0];
        // this.selectItem(newSelectedItem);

        // 更新显示
        this.updateItemDisplay();
    }

    createListItem(item) {
        const listItem = $('<div>').css({
            'cursor': 'pointer',
            'border-radius': '3px',
            'color': this.itemTextColor,
            'width': '100%',
            'min-height': this.height + 'px',
            'padding': '0 10px',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            'transition': 'background-color 0.3s ease-in-out'
        });
        listItem.text(item.name);

        // 使用事件委托，避免直接绑定到每个项目
        listItem.attr('data-value', item.value);

        return listItem;
    }
}