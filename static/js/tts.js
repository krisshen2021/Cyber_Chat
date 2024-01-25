  export class msTTS extends EventTarget{
  constructor() {
    super();
  }
  tts(inputText, speaker, styletone, apimkey) {
    this.tts_text = inputText;
    this.speaker = speaker;
    this.styletone = styletone;
    this.apimkey = apimkey;
    this.currentTime = 0;
    // this.audioplayer = new Audio();
    // 设置请求头
    const headers = {
      "X-Microsoft-OutputFormat": "riff-8khz-16bit-mono-pcm",
      "Content-Type": "application/ssml+xml",
      "Ocp-Apim-Subscription-Key": this.apimkey,
    };

    // 设置请求体
    const data =
      `
        <speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="zh-CN">
    <voice name='` +
      this.speaker +
      `'>
    <mstts:express-as style="` +
      this.styletone +
      `" styledegree="2">
    <prosody rate="-1.00%" pitch="0%">
      ` +
      this.tts_text +
      `
       </prosody>
      </mstts:express-as>
    </voice>
  </speak>`;

    // 发送 POST 请求
    axios
      .post(
        "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1",
        data,
        { headers, responseType: "arraybuffer" }
      )
      .then((response) => {
        // 获取返回的音频内容
        const audioData = response.data;
        console.log(audioData);
        let blob = new Blob([audioData], { type: "audio/wav" });
        let url = window.URL.createObjectURL(blob);
        let audioplayer = new Audio(url);
        audioplayer.onplay = () => {
          let event = new Event('onPlay');
          this.dispatchEvent(event);
        };
        audioplayer.onended = () => {
          URL.revokeObjectURL(url);
          let event = new Event('onStop');
          this.dispatchEvent(event);
          audioplayer = null;
        };
        audioplayer.ontimeupdate = () => {
          let event = new Event('onUpdate');
          this.currentTime = Math.round(audioplayer.currentTime*1000)
          this.dispatchEvent(event);
        }
        audioplayer.play();
      })
      .catch((error) => {
        // 处理请求错误
        console.error("Error:", error);
      });
  }
}
