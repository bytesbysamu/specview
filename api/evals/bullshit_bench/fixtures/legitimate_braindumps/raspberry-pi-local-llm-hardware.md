A very cheap Raspberry Pi-based local LLM device. Budget: under 100 CHF for the base unit.

The core idea: take the cheapest viable Raspberry Pi (Pi 5 8GB, ~75 CHF), install a self-contained OS image with a local LLM (llama.cpp running a quantized sub-4B model like Phi-3-mini or Gemma 2B), and ship it as a standalone product. No internet required. No cloud. No account. No data leaves the device.

User interaction: voice-first via local speech-to-text (whisper.cpp) and text-to-speech (piper). Minimal physical interface — maybe a small OLED display or e-ink screen, a few LEDs for status, a microphone, and a speaker. Think appliance, not computer.

The pitch: an AI that lives in your house, works without wifi, and never sends your data anywhere. The dumb phone of AI — intentionally limited, and that is the point.

Hardware BOM target: Raspberry Pi 5 8GB (~75 CHF), case, SD card, power supply, USB microphone, small speaker, optional OLED display. Total under 150 CHF retail.

Software stack: custom Linux image (Raspberry Pi OS Lite), llama.cpp for inference, whisper.cpp for STT, piper for TTS, a simple Python orchestrator that ties voice pipeline together. Boot to ready in under 60 seconds.

Performance reality: ~5-10 tokens/sec on Pi 5 with Q4 quantized 3.8B model. Voice round-trip (STT + inference + TTS) ~15-20 seconds. Usable for Q&A, summarization, simple reasoning, journaling, language practice. Not competing with cloud LLMs on capability — competing on trust and simplicity.

Go-to-market: start by hand-assembling 10-20 units. Sell direct. Validate demand. If it works, design a custom PCB or at minimum a standardized assembly process. Target audiences: privacy-conscious users, educators, developing regions with unreliable internet, elderly users who want a simple voice assistant without surveillance.

The commoditization angle: if this works, the unit cost drops with volume. Raspberry Pi foundation already does scale. The software image is the real product — flash it onto any Pi and it works. Could eventually open-source the image and sell pre-assembled units as the convenience play.

Key questions to figure out: which model gives the best quality-per-token at sub-4B parameters? Can we get voice round-trip under 10 seconds? What is the minimal viable interaction that feels useful, not frustrating? Is there a form factor that feels like a product and not a dev board?
