# iTranslate Sales Demo

This directory contains the assets, documentation, and the deployable Streamlit application designed for the iTranslate sales pitch.

## 🚀 Streamlit Cloud Deployment

The interactive demo has been structured into the `app/` directory specifically for effortless deployment to [Streamlit Community Cloud](https://share.streamlit.io/) or platforms like Render/Heroku.

### Deployment Instructions (Streamlit Cloud)
1. Push this repository to GitHub.
2. Log into [Streamlit Community Cloud](https://share.streamlit.io/).
3. Click **New app**.
4. Select your repository, branch, and set the **Main file path** to:
   ```text
   itranslate_demo/app/app.py
   ```
5. Click **Advanced Settings** before deploying and add your API key to the Secrets block:
   ```toml
   ASSEMBLYAI_API_KEY = "your_actual_key_here"
   ```
6. Click **Deploy!**

### Directory Structure
*   📁 **`app/`**: Contains the deployable Streamlit application and `requirements.txt`.
    *   `app.py`: The main Streamlit UI rendering loop.
    *   `assemblyai_service.py`: The background WebSocket controller bridging the STT streams.
    *   `requirements.txt`: Python dependencies required by the cloud host.
*   📄 **`approach_document.md`**: Executive summary of the low-latency STT architectural integration.
*   📄 **`iTranslate_Pitch_Deck.md`**: The exact narrative and script points for the Account Executive.

## Running Locally

If you need to run the app locally for development:
```bash
cd itranslate_demo/app
pip install -r requirements.txt
export ASSEMBLYAI_API_KEY="your_api_key_here"
streamlit run app.py
```
