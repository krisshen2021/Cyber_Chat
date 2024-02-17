// AudioGenerator.js
export class AudioGenerator extends EventTarget{
    constructor() {
        // 初始化代码（如果需要的话）
        super();
    }

    gen_audio({text = "hello world", url_api = "http://localhost:8020/tts_to_audio/", speaker = "female_01", language_input = "en"} = {}) {
        fetch(url_api, {
            method: 'POST',
            headers: {
                'accept': 'audio/wav',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                speaker_wav: speaker,
                language: language_input
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.blob(); // 获取响应体作为Blob对象
        })
        .then(blob => {
            const url = URL.createObjectURL(blob); // 从Blob对象创建一个URL
            const audio = new Audio(url); // 创建一个新的Audio对象并指定源为上面创建的URL
            audio.play(); // 播放音频
            audio.onended = function() {
                URL.revokeObjectURL(url); // 音频播放完成后，释放创建的URL
            };
        })
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
        });
    }
}
