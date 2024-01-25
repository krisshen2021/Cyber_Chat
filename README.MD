**The Cyber Chat V1.0**
---
**Features**
---
- ***Endless Enviroment Experiences*** 
Dynamically generate chat background and avatar base on character card and chatting emotions
- ***Immersive Chatting Excitments*** 
Dynamically generate scene images base on character response, never repeat.(especially for ***NSFW*** !!!)


**1. Install Cyber Chat**
```bash
python -m venv venv
```
then activate the venv,
or use conda:
```bash
conda create -n tabbyAPI python=3.10
conda activate tabbyAPI
```
Install required Python Packages
```bash
pip install -r requirement.txt
```
**2. Preparation Services**
- **TabbyAPI - use my another customized Tabby forked repo**
    ```bash 
    git clone https://github.com/krisshen2021/tabbyAPI 
    ```
    - After install , start two server, one for chat, one for rephase
        - for example (http://127.0.0.1:5001 & http://127.0.0.1:5003)

- **Stable Diffusion webUI**
        - start in API mode, get the checkpoint name 
        - for example (http://127.0.0.1:7680), checkpoint name: "realcartoon25D_v2.safetensors [1736b1efbe]"
- **Configuration**
    - Edit ./config/config.yml to set 3 server addresses(you started servers above) and the StableDiffusion preferences
    - Edit ./conifg/personas/[character].yml to set character cards and specific LLM model and preferences.

**3. Run Cyber Chat**
```bash
python cyberchat.py
```