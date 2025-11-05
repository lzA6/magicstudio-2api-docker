document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const apiKeyInput = document.getElementById('api-key');
    const modelSelect = document.getElementById('model-select');
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    const countSlider = document.getElementById('count-slider');
    const countValue = document.getElementById('count-value');
    const imageGrid = document.getElementById('image-grid');
    const spinner = document.getElementById('spinner');
    const errorMessage = document.getElementById('error-message');
    const placeholder = document.getElementById('placeholder');

    async function populateModels() {
        modelSelect.innerHTML = '';
        modelSelect.disabled = true;
        generateBtn.disabled = true;
        hideError();

        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) {
            const placeholderOption = document.createElement('option');
            placeholderOption.textContent = "请输入API Key以加载模型";
            modelSelect.appendChild(placeholderOption);
            return;
        }

        const loadingOption = document.createElement('option');
        loadingOption.textContent = "正在加载模型...";
        modelSelect.appendChild(loadingOption);

        try {
            const response = await fetch('/v1/models', {
                headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '获取模型列表失败。');
            }
            
            modelSelect.innerHTML = '';
            result.data.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.id;
                modelSelect.appendChild(option);
            });
            
            modelSelect.disabled = false;
            generateBtn.disabled = false;

        } catch (error) {
            showError(`模型加载失败: ${error.message}. 请检查您的 API Key.`);
            modelSelect.innerHTML = '';
            const errorOption = document.createElement('option');
            errorOption.textContent = "加载失败，请检查API Key";
            modelSelect.appendChild(errorOption);
        }
    }

    async function handleGenerate() {
        const apiKey = apiKeyInput.value.trim();
        const prompt = promptInput.value.trim();
        const selectedModel = modelSelect.value;

        if (!apiKey || !prompt) {
            showError("请确保 API Key 和提示词都已填写。");
            return;
        }
        if (!selectedModel || modelSelect.disabled) {
            showError("模型未成功加载或未选择，请检查您的 API Key。");
            return;
        }

        setLoading(true);

        const payload = {
            model: selectedModel,
            prompt: prompt,
            n: parseInt(countSlider.value, 10),
            response_format: "b64_json"
        };

        try {
            const response = await fetch('/v1/images/generations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '生成失败，未知错误。');
            }

            if (result.data && result.data.length > 0) {
                displayImages(result.data);
            } else {
                throw new Error('API 返回了成功状态，但没有图片数据。');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function displayImages(data) {
        imageGrid.innerHTML = '';
        data.forEach(item => {
            if (item.b64_json) {
                const imgContainer = document.createElement('div');
                imgContainer.className = 'image-container';
                const img = document.createElement('img');
                img.src = `data:image/png;base64,${item.b64_json}`;
                img.alt = 'Generated Image';
                imgContainer.appendChild(img);
                imageGrid.appendChild(imgContainer);
            }
        });
    }

    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        spinner.classList.toggle('hidden', !isLoading);
        placeholder.classList.toggle('hidden', isLoading || imageGrid.children.length > 0);
        if (isLoading) {
            imageGrid.innerHTML = '';
            hideError();
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        imageGrid.innerHTML = '';
        placeholder.classList.add('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    countSlider.addEventListener('input', () => countValue.textContent = countSlider.value);
    generateBtn.addEventListener('click', handleGenerate);
    apiKeyInput.addEventListener('change', populateModels);

    populateModels();
});
