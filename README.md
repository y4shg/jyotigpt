# JyotiGPT 👋

![GitHub stars](https://img.shields.io/github/stars/jyotigpt/jyotigpt?style=social)
![GitHub forks](https://img.shields.io/github/forks/jyotigpt/jyotigpt?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/jyotigpt/jyotigpt?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/jyotigpt/jyotigpt)
![GitHub language count](https://img.shields.io/github/languages/count/jyotigpt/jyotigpt)
![GitHub top language](https://img.shields.io/github/languages/top/jyotigpt/jyotigpt)
![GitHub last commit](https://img.shields.io/github/last-commit/jyotigpt/jyotigpt?color=red)
![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Follama-jyotigpt%2Follama-wbui&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)
[![Discord](https://img.shields.io/badge/Discord-JyotiGPT-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/tjbck)

**JyotiGPT is an [extensible](https://docs.jyotigpt.com/features/plugin/), feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline.** It supports various LLM runners like **Ollama** and **OpenAI-compatible APIs**, with **built-in inference engine** for RAG, making it a **powerful AI deployment solution**.

![JyotiGPT Demo](./demo.gif)

> [!TIP]  
> **Looking for an [Enterprise Plan](https://docs.jyotigpt.com/enterprise)?** – **[Speak with Our Sales Team Today!](mailto:sales@jyotigpt.com)**
>
> Get **enhanced capabilities**, including **custom theming and branding**, **Service Level Agreement (SLA) support**, **Long-Term Support (LTS) versions**, and **more!**

For more information, be sure to check out our [JyotiGPT Documentation](https://docs.jyotigpt.com/).

## Key Features of JyotiGPT ⭐

- 🚀 **Effortless Setup**: Install seamlessly using Docker or Kubernetes (kubectl, kustomize or helm) for a hassle-free experience with support for both `:ollama` and `:cuda` tagged images.

- 🤝 **Ollama/OpenAI API Integration**: Effortlessly integrate OpenAI-compatible APIs for versatile conversations alongside Ollama models. Customize the OpenAI API URL to link with **LMStudio, GroqCloud, Mistral, OpenRouter, and more**.

- 🛡️ **Granular Permissions and User Groups**: By allowing administrators to create detailed user roles and permissions, we ensure a secure user environment. This granularity not only enhances security but also allows for customized user experiences, fostering a sense of ownership and responsibility amongst users.

- 📱 **Responsive Design**: Enjoy a seamless experience across Desktop PC, Laptop, and Mobile devices.

- 📱 **Progressive Web App (PWA) for Mobile**: Enjoy a native app-like experience on your mobile device with our PWA, providing offline access on localhost and a seamless user interface.

- ✒️🔢 **Full Markdown and LaTeX Support**: Elevate your LLM experience with comprehensive Markdown and LaTeX capabilities for enriched interaction.

- 🎤📹 **Hands-Free Voice/Video Call**: Experience seamless communication with integrated hands-free voice and video call features, allowing for a more dynamic and interactive chat environment.

- 🛠️ **Model Builder**: Easily create Ollama models via the JYOTIGPT. Create and add custom characters/agents, customize chat elements, and import models effortlessly through [JyotiGPT Community](https://jyotigpt.com/) integration.

- 🐍 **Native Python Function Calling Tool**: Enhance your LLMs with built-in code editor support in the tools workspace. Bring Your Own Function (BYOF) by simply adding your pure Python functions, enabling seamless integration with LLMs.

- 📚 **Local RAG Integration**: Dive into the future of chat interactions with groundbreaking Retrieval Augmented Generation (RAG) support. This feature seamlessly integrates document interactions into your chat experience. You can load documents directly into the chat or add files to your document library, effortlessly accessing them using the `#` command before a query.

- 🔍 **Web Search for RAG**: Perform web searches using providers like `SearXNG`, `Google PSE`, `Brave Search`, `serpstack`, `serper`, `Serply`, `DuckDuckGo`, `TavilySearch`, `SearchApi` and `Bing` and inject the results directly into your chat experience.

- 🌐 **Web Browsing Capability**: Seamlessly integrate websites into your chat experience using the `#` command followed by a URL. This feature allows you to incorporate web content directly into your conversations, enhancing the richness and depth of your interactions.

- 🎨 **Image Generation Integration**: Seamlessly incorporate image generation capabilities using options such as AUTOMATIC1111 API or ComfyUI (local), and OpenAI's DALL-E (external), enriching your chat experience with dynamic visual content.

- ⚙️ **Many Models Conversations**: Effortlessly engage with various models simultaneously, harnessing their unique strengths for optimal responses. Enhance your experience by leveraging a diverse set of models in parallel.

- 🔐 **Role-Based Access Control (RBAC)**: Ensure secure access with restricted permissions; only authorized individuals can access your Ollama, and exclusive model creation/pulling rights are reserved for administrators.

- 🌐🌍 **Multilingual Support**: Experience JyotiGPT in your preferred language with our internationalization (i18n) support. Join us in expanding our supported languages! We're actively seeking contributors!

- 🧩 **Pipelines, JyotiGPT Plugin Support**: Seamlessly integrate custom logic and Python libraries into JyotiGPT using [Pipelines Plugin Framework](https://github.com/jyotigpt/pipelines). Launch your Pipelines instance, set the OpenAI URL to the Pipelines URL, and explore endless possibilities. [Examples](https://github.com/jyotigpt/pipelines/tree/main/examples) include **Function Calling**, User **Rate Limiting** to control access, **Usage Monitoring** with tools like Langfuse, **Live Translation with LibreTranslate** for multilingual support, **Toxic Message Filtering** and much more.

- 🌟 **Continuous Updates**: We are committed to improving JyotiGPT with regular updates, fixes, and new features.

Want to learn more about JyotiGPT's features? Check out our [JyotiGPT documentation](https://docs.jyotigpt.com/features) for a comprehensive overview!

## 🔗 Also Check Out JyotiGPT Community!

Don't forget to explore our sibling project, [JyotiGPT Community](https://jyotigpt.com/), where you can discover, download, and explore customized Modelfiles. JyotiGPT Community offers a wide range of exciting possibilities for enhancing your chat interactions with JyotiGPT! 🚀

## How to Install 🚀

### Installation via Python pip 🐍

JyotiGPT can be installed using pip, the Python package installer. Before proceeding, ensure you're using **Python 3.11** to avoid compatibility issues.

1. **Install JyotiGPT**:
   Open your terminal and run the following command to install JyotiGPT:

   ```bash
   pip install jyotigpt
   ```

2. **Running JyotiGPT**:
   After installation, you can start JyotiGPT by executing:

   ```bash
   jyotigpt serve
   ```

This will start the JyotiGPT server, which you can access at [http://localhost:8080](http://localhost:8080)

### Quick Start with Docker 🐳

> [!NOTE]  
> Please note that for certain Docker environments, additional configurations might be needed. If you encounter any connection issues, our detailed guide on [JyotiGPT Documentation](https://docs.jyotigpt.com/) is ready to assist you.

> [!WARNING]
> When using Docker to install JyotiGPT, make sure to include the `-v jyotigpt:/app/backend/data` in your Docker command. This step is crucial as it ensures your database is properly mounted and prevents any loss of data.

> [!TIP]  
> If you wish to utilize JyotiGPT with Ollama included or CUDA acceleration, we recommend utilizing our official images tagged with either `:cuda` or `:ollama`. To enable CUDA, you must install the [Nvidia CUDA container toolkit](https://docs.nvidia.com/dgx/nvidia-container-runtime-upgrade/) on your Linux/WSL system.

### Installation with Default Configuration

- **If Ollama is on your computer**, use this command:

  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v jyotigpt:/app/backend/data --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:main
  ```

- **If Ollama is on a Different Server**, use this command:

  To connect to Ollama on another server, change the `OLLAMA_BASE_URL` to the server's URL:

  ```bash
  docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v jyotigpt:/app/backend/data --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:main
  ```

- **To run JyotiGPT with Nvidia GPU support**, use this command:

  ```bash
  docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v jyotigpt:/app/backend/data --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:cuda
  ```

### Installation for OpenAI API Usage Only

- **If you're only using OpenAI API**, use this command:

  ```bash
  docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v jyotigpt:/app/backend/data --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:main
  ```

### Installing JyotiGPT with Bundled Ollama Support

This installation method uses a single container image that bundles JyotiGPT with Ollama, allowing for a streamlined setup via a single command. Choose the appropriate command based on your hardware setup:

- **With GPU Support**:
  Utilize GPU resources by running the following command:

  ```bash
  docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v jyotigpt:/app/backend/data --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:ollama
  ```

- **For CPU Only**:
  If you're not using a GPU, use this command instead:

  ```bash
  docker run -d -p 3000:8080 -v ollama:/root/.ollama -v jyotigpt:/app/backend/data --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:ollama
  ```

Both commands facilitate a built-in, hassle-free installation of both JyotiGPT and Ollama, ensuring that you can get everything up and running swiftly.

After installation, you can access JyotiGPT at [http://localhost:3000](http://localhost:3000). Enjoy! 😄

### Other Installation Methods

We offer various installation alternatives, including non-Docker native installation methods, Docker Compose, Kustomize, and Helm. Visit our [JyotiGPT Documentation](https://docs.jyotigpt.com/getting-started/) or join our [Discord community](https://discord.gg/5rJgQTnV4s) for comprehensive guidance.

### Troubleshooting

Encountering connection issues? Our [JyotiGPT Documentation](https://docs.jyotigpt.com/troubleshooting/) has got you covered. For further assistance and to join our vibrant community, visit the [JyotiGPT Discord](https://discord.gg/5rJgQTnV4s).

#### JyotiGPT: Server Connection Error

If you're experiencing connection issues, it’s often due to the JYOTIGPT docker container not being able to reach the Ollama server at 127.0.0.1:11434 (host.docker.internal:11434) inside the container . Use the `--network=host` flag in your docker command to resolve this. Note that the port changes from 3000 to 8080, resulting in the link: `http://localhost:8080`.

**Example Docker Command**:

```bash
docker run -d --network=host -v jyotigpt:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name jyotigpt --restart always ghcr.io/jyotigpt/jyotigpt:main
```

### Keeping Your Docker Installation Up-to-Date

In case you want to update your local Docker installation to the latest version, you can do it with [Watchtower](https://containrrr.dev/watchtower/):

```bash
docker run --rm --volume /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --run-once jyotigpt
```

In the last part of the command, replace `jyotigpt` with your container name if it is different.

Check our Updating Guide available in our [JyotiGPT Documentation](https://docs.jyotigpt.com/getting-started/updating).

### Using the Dev Branch 🌙

> [!WARNING]
> The `:dev` branch contains the latest unstable features and changes. Use it at your own risk as it may have bugs or incomplete features.

If you want to try out the latest bleeding-edge features and are okay with occasional instability, you can use the `:dev` tag like this:

```bash
docker run -d -p 3000:8080 -v jyotigpt:/app/backend/data --name jyotigpt --add-host=host.docker.internal:host-gateway --restart always ghcr.io/jyotigpt/jyotigpt:dev
```

### Offline Mode

If you are running JyotiGPT in an offline environment, you can set the `HF_HUB_OFFLINE` environment variable to `1` to prevent attempts to download models from the internet.

```bash
export HF_HUB_OFFLINE=1
```

## What's Next? 🌟

Discover upcoming features on our roadmap in the [JyotiGPT Documentation](https://docs.jyotigpt.com/roadmap/).

## License 📜

This project is licensed under the [BSD-3-Clause License](LICENSE) - see the [LICENSE](LICENSE) file for details. 📄

## Support 💬

If you have any questions, suggestions, or need assistance, please open an issue or join our
[JyotiGPT Discord community](https://discord.gg/5rJgQTnV4s) to connect with us! 🤝

## Star History

<a href="https://star-history.com/#jyotigpt/jyotigpt&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=jyotigpt/jyotigpt&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=jyotigpt/jyotigpt&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=jyotigpt/jyotigpt&type=Date" />
  </picture>
</a>

---

Created by [Timothy Jaeryang Baek](https://github.com/tjbck) - Let's make JyotiGPT even more amazing together! 💪
