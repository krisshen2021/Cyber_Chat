## **Cyber Chat V1.0**

**_Endless Enviroment Experiences_**
- Fully support for remote and local inference
  - OAI, Ollama, Tabbyapi, AWSbedrock, cohere, claude, deepseek ...
- TTS/STT fully integrated, can use remote api or local xtts server
- More accurate dynamic live background/avatar and face expression base on conversatino progress
- Inteligence sentence completion base on context in dialogue
- Inteligence customize command injection integrated in user input to create more variable and exciting chat.
- Special dynamic NSFW senario pic base on latest dialogue
- Create decent character with assistance of  A.I system, fully release the great story experience
- Optimize dynampic picture generate for low speed mobile network, lighting speed!

**Install and Run Cyber Chat**
Step 1.
```bash
git pull https://github.com/krisshen2021/Cyber_Chat.git
cd Cyber_Chat
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
after install depenencies, 
you need to start your stable diffusion server(must, auto1111 only).

Step 2.
open a new terminal and run
```bash
cd server
source ../venv/bin/activate
mv .env_sample to .env
nano .env #set up all api keys you own
python start_server.py
```
Then:
- input stable diffusion address and setup info
- select remote or local inference endpoint
  - if select local, you need to start tabbyapi server(start in completion mode) or xtts api server
  - if select remote, you need to setup your own api key in .env

After server started, back to current terminal and run

```bash
python cyberchat.py
```
tabbyapi server repo:
https://github.com/theroyallab/tabbyAPI.git

xtts api server repo:
https://github.com/daswer123/xtts-api-server.git

auto1111 repo:
https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
