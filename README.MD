## **The Cyber Chat V1.0**

**_Endless Enviroment Experiences_**
- Fully support for remote and local inference
- OAI, Ollama, Tabbyapi, AWSbedrock, cohere, claude, deepseek ..... fully support
- TTS/STT fully integrated, can use remote api or local xtts server
- More accurate dynamic live background/avatar and face expression base on conversatino progress
- Inteligence sentence completion base on context in dialogue
- Inteligence customize command injection integrated in user input to create more variable and exciting chat.
- Special dynamic NSFW senario pic base on latest dialogue
- Create decent character with assistance of  A.I system, fully release the great story experience
- Optimize dynampic picture generate for low speed mobile network, lighting speed!

**Install and Run Cyber Chat**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

open a new terminal and run

```bash
cd server
mv .env_sample to .env
nano .env #set up all api keys you own
python start_server.py
```
Then:
- input stable diffusion config info
- select remote or local inference endpoint
  - if select local, you need to start tabbyapi server(install by yourself, start in completion mode)
  - if select remote, you need to setup your own api key in .env

After server started, back to current terminal and run

```bash
python cyberchat.py
```
