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

    onMouseDown(e) {
        this.isDragging = true;
        const rect = this.element[0].getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        this.startAngle = this.calculateAngle(e.clientX, e.clientY, centerX, centerY);
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

    onMouseUp() {
        this.isDragging = false;
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