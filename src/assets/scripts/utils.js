let corsProxy = "https://corsproxy.io/?";
const fetch_cors = async (url) => {
    try {
        return (await fetch(url));
    } catch (e) {
        if (url.startsWith(corsProxy)) {
            showNotification("Error", `Error while downloading: ${e}`);
            return null;
        }
        return fetch_cors(corsProxy + url);
    }
}

const download = (content, filename) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

const showNotification = (title, content, color = "red", time = 8000) => {
    document.querySelector(".notification__container").insertAdjacentHTML("beforeend", `
        <div class="col primary">
            <p class="title">${title}</p>
            <p class="content">${content}</p>
            <div class="bar" style="background: ${color};"></div>
        </div>
    `);
    let element = document.querySelector(".notification__container div.primary:last-of-type");
    if (!element || time == null) return;
    element.querySelector(".bar").animate([ { width: '100%', opacity: 1 }, { width: '0%', opacity: 0 } ], { duration: time, fill: 'forwards' } ).onfinish = () => element.remove();
}

const download_url = (url, filename) => {
    fetch_cors(url).then(x => x.blob()).then(x => download(x, filename));
}