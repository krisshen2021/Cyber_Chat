export class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.resetRecordPromise();
    }

    resetRecordPromise() {
        this.recordPromise = new Promise((resolve, reject) => {
            this.recordResolve = resolve;
            this.recordReject = reject;
        });
    }

    async startRecording() {
        try {
            this.resetRecordPromise();
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];
            this.isRecording = true;

            this.mediaRecorder.addEventListener('dataavailable', (event) => {
                this.audioChunks.push(event.data);
            });

            this.mediaRecorder.addEventListener('stop', () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                this.cleanup();
                this.recordResolve(audioBlob);
            });

            this.mediaRecorder.start();
        } catch (error) {
            this.cleanup();
            this.recordReject(error);
            throw error;
        }
    }

    async stopRecording() {
        this.isRecording = false;
        this.mediaRecorder.stop();
        return this.recordPromise;
    }

    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
        }
        this.mediaRecorder = null;
        this.stream = null;
        this.audioChunks = [];       
    }
}