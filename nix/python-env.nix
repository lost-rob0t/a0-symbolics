{ pkgs, focused ? false }:
let
  ps = pkgs.python312Packages;

  patchright = ps.buildPythonPackage {
    pname = "patchright";
    version = "1.61.2";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/a2/b5/c76dcda275cb0d9651321e343f3268609ae24cef196bff56751754ffba16/patchright-1.61.2-py3-none-manylinux1_x86_64.whl";
      hash = "sha256-VFvfLAu1+a14qzFekcjCmQzGpwLn8YZQtx/hBxBJtcE=";
    };
    dependencies = [ ps.greenlet ps.pyee ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  pyreqwestImpersonate = ps.buildPythonPackage {
    pname = "pyreqwest-impersonate";
    version = "0.5.3";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/1f/ec/95514b593277c77e371292001cc1837790362749d5839f4e4e5f1e0d7a20/pyreqwest_impersonate-0.5.3-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
      hash = "sha256-fp0umBpSX7csFSH0VOVYHSx6Ox/PHJfArPy3qSPYzz4=";
    };
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  duckduckgoSearch = ps.buildPythonPackage {
    pname = "duckduckgo-search";
    version = "6.1.12";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/3c/08/2295882d25ba18306c9ee5b2a1581cf944dad6370e36716de3c4d944c282/duckduckgo_search-6.1.12-py3-none-any.whl";
      hash = "sha256-GjxnTeSpMH/noFt2cmwr8A2Kl8QI/0Q9B9fHqKwmTtI=";
    };
    dependencies = [ ps.click pyreqwestImpersonate ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  langsmith = ps.buildPythonPackage {
    pname = "langsmith";
    version = "0.3.30";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/d8/3a/2c2d50e46a5e0b33411faea1200e93cca84e0534e833934e76692543822d/langsmith-0.3.30-py3-none-any.whl";
      hash = "sha256-gNWRpMYsFJULpJe7i1Za2b2NB+ECtkORbw0q8aey2q8=";
    };
    dependencies = with ps; [ httpx orjson packaging pydantic requests requests-toolbelt zstandard ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  langchainCore = ps.buildPythonPackage {
    pname = "langchain-core";
    version = "0.3.49";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/dd/35/27164f5f23517be8639b518130e6235293dae52c41988790e0b50dd7ba11/langchain_core-0.3.49-py3-none-any.whl";
      hash = "sha256-iT7kLJrxO/Ki2MLsFboApcc8zN4hor0AUjTuDniivfg=";
    };
    dependencies = (with ps; [ jsonpatch packaging pydantic pyyaml requests tenacity typing-extensions ]) ++ [ langsmith ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  langchainTextSplitters = ps.buildPythonPackage {
    pname = "langchain-text-splitters";
    version = "0.3.7";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/d3/85/b7a34b6d34bcc89a2252f5ffea30b94077ba3d7adf72e31b9e04e68c901a/langchain_text_splitters-0.3.7-py3-none-any.whl";
      hash = "sha256-MbqCYBPj9WM1nXx/HpmxzblIl/ZlZ17lBXGMEW5+IK0=";
    };
    dependencies = [ langchainCore ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  langchain = ps.buildPythonPackage {
    pname = "langchain";
    version = "0.3.20";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/b5/d4/afe8174838bdd3baba5d6a19e9f3af4c54c5db1ab4d66ef0b650c6157919/langchain-0.3.20-py3-none-any.whl";
      hash = "sha256-JzKH+OYf/ffoEc+HmeanHpOBMluGJf1mGJAPq6ec/dA=";
    };
    dependencies = (with ps; [ pydantic pyyaml requests sqlalchemy ]) ++ [ langchainCore langchainTextSplitters langsmith ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  langchainCommunity = ps.buildPythonPackage {
    pname = "langchain-community";
    version = "0.3.19";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/2b/a3/6718deba2c30db991c6b000d23fa062441daa576eb1e520cb2edc2729e2f/langchain_community-0.3.19-py3-none-any.whl";
      hash = "sha256-JoznsyLA0ZYde6salBnW/zDJmtCUh9ykjUc4m2mHWxY=";
    };
    dependencies = (with ps; [ aiohttp dataclasses-json httpx-sse numpy pydantic-settings pyyaml requests sqlalchemy tenacity ]) ++ [ langchain langchainCore langsmith ];
    doCheck = false;
    dontCheckRuntimeDeps = true;
  };
  focusedPackages = (with ps; [
    crontab cryptography faiss-cpu flask gitpython giturlparse litellm markdown nest-asyncio paramiko
    pathspec pillow pydantic python-dotenv python-socketio pytest pytest-asyncio pytest-mock
    pytz simpleeval tiktoken watchdog webcolors
  ]) ++ [ langchainCore langchain langchainCommunity ];
  fullPackages = (with ps; [
    a2wsgi aiogram asgiref beautifulsoup4 boto3 chardet crontab
    duckduckgoSearch exchangelib faiss-cpu fastmcp flask gitpython
    giturlparse html2text imapclient langchain langchainCommunity
    langchainCore litellm lxml-html-clean markdown markdownify mcp
    nest-asyncio newspaper3k openai openai-whisper paramiko pathspec
    pdf2image psutil pydantic pymupdf pypdf pytesseract python-dotenv
    python-socketio pytz sentence-transformers simpleeval soundfile
    tiktoken unstructured unstructured-client uvicorn watchdog webcolors
    wsproto pytest pytest-asyncio pytest-mock
  ]) ++ [ patchright ];
  packages = if focused then focusedPackages else fullPackages;
in
pkgs.python312.withPackages (_: packages)
