## Inspiration
As technology becomes more embedded in everyday life, so do concerns about privacy and personal security. 

Between public workspaces, shared apartments, and increasingly digital lifestyles, there is a growing need for adaptive security systems that feel seamless rather than intrusive. We wanted to build something that combined computer vision, automation, and privacy into a practical, real-world tool.

Percepta was born from that idea: a smart, real-time vision system that can detect presence, recognize identity, and automatically protect your device when needed.

## What it does
Percepta is a real-time computer vision security system that:

- Detects faces using a live webcam feed  
- Recognizes registered users using deep learning embeddings  
- Automatically locks the system when no authorized face is detected  
- Supports a **Public Mode** where temporary users can register and have their data wiped after their session  
- Logs security events for monitoring and auditing  

It turns a normal webcam into an adaptive identity-aware security layer.
## How we built it
Percepta was built using:

- **Python** for system orchestration  
- **OpenCV** for real-time video capture  
- **facenet-pytorch (MTCNN + InceptionResnetV1)** for face detection and embedding extraction  
- **NumPy** for vector comparison and similarity calculations  
- **Multiprocessing** for managing overlays and system responsiveness  
- **Tkinter** for a lightweight status interface  
- **Smalltalk** for a clean web ui for logs

The system pipeline works like this:

1. Capture frame from webcam  
2. Detect faces using MTCNN  
3. Generate 512-dimension face embeddings  
4. Compare embeddings against stored vectors using cosine similarity  
5. Trigger security logic (unlock, standby, auto-lock, wipe session data)  

We designed the architecture to be modular so detection, recognition, GUI, and security logic are separated into clean components.

## Challenges we ran into
- **Real-time performance tuning** : balancing detection accuracy with low latency  
- **State management** : properly handling transitions between known, unknown, and no-face states  
- **Public mode data wiping** : ensuring temporary users are fully removed without corrupting the database  
- **Concurrency issues** : managing multiprocessing without race conditions  
- **User experience design** : making feedback clear without cluttering the screen
## Accomplishments that we're proud of
- Successfully built a **fully functional real-time face recognition system**
- Implemented a clean **auto-lock mechanism** tied to presence detection  
- Designed a unique **Public Mode** that treats users as temporary sessions  
- Created a modular architecture that can scale into larger automation systems  
- Achieved stable real-time inference performance  
## What we learned
- Threshold tuning and edge-case handling matter more than model choice  
- Clean architecture prevents chaos when adding features  
- State machines are critical in security logic  
## What's next for Percepta
Percepta is just the beginning. Next steps include:

- Gesture-based system control  
- Encrypted face embedding storage  
- Cross-platform system integration  
- Cloud dashboard for remote monitoring  
- Hardware integration (Raspberry Pi / edge device deployment)  

Long term, we envision Percepta evolving into a broader adaptive privacy and automation platform where your environment intelligently responds to presence, identity, and context.

