// AudioGenerator.js
export class AudioGenerator extends EventTarget{
    constructor() {
        // 初始化代码（如果需要的话）
        super();
    }

    gen_audio({text = "hello world", url_api = "http://127.0.0.1:8020/tts_to_audio", speaker_wav = "female_01", language = "en", mainserver = "http://127.0.0.1:5001/v1/xtts"} = {}) {
        fetch(mainserver, {
            method: 'POST',
            headers: {
                'accept': 'audio/wav',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                speaker_wav: speaker_wav,
                language: language,
                server_url: url_api
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
