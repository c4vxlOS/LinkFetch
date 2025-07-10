let data;

const processingModal = document.querySelector(".processing__modal");
const completeModal = document.querySelector(".complete__modal");
const formatPicker = completeModal.querySelector("#complete__select__format");
const exportOptions = completeModal.querySelector(".options");
const fileServerExportModal = document.querySelector(".fileserver__export__modal");

const submit = async () => {
    processingModal.classList.add("active");
    
    fetch(`/fetch/${document.querySelector('#url__input').value}`).then(x => x.json()).then(x => {
        data = x;
        processingModal.classList.remove("active");
        complete(x);
    });
}

const complete = (data) => {
    const get_format = () => {
        const id = Number.parseInt(formatPicker.value);
        return data.formats[id];
    };

    completeModal.classList.add("active");
    completeModal.querySelector(".thumbnail").src = data.thumbnail;
    completeModal.querySelector(".thumbnail").style.display = "none" ? !data.thumbnail : "unset";
    completeModal.querySelector(".preview__title").textContent = data.title;
    
    formatPicker.innerHTML = data.formats.map((x, i) => {
            x = `${x.type.toLocaleUpperCase()}: ${x.quality} (${x.format})`;
            return `<option value="${i}">${x}</option>`;
    }).join("");

    formatPicker.onchange = () => { completeModal.querySelector("#complete__url__field").value = get_format().url; };
    formatPicker.onchange();

    // Set actions
    const set_action = (name, action) => { exportOptions.querySelector(`*[data-action=${name}]`).onclick = action; };
    set_action("copy", () => {
        navigator.clipboard?.writeText(get_format().url)
            .then(() => showNotification('Success', 'Successfully copied url.', 'green'))
            .catch((e) => showNotification('Error', 'Something went wrong.')) || showNotification("Error", "Clipboard api not working on HTTP!")
    });

    set_action("visit", () => {
        const format = get_format();
        window.open(`/stream/${format.type}/${format.quality}/${data.src}`);
    });
    set_action("download", () => {
        showNotification("Downloading", "Starting download...", "green");
        const format = get_format();
        download_url(`/direct_stream/${format.url}`, format.filename);
    });
    set_action("fileserver", async () => {
        const fsi = await (await fetch("/fileserver")).json();
        fileServerExportModal.querySelector("#export__fileserver__instance").value = fsi || "";
        fileServerExportModal.classList.add("active");
        fileServerExportModal.querySelector("button").onclick = () => {
            const _fsi = fileServerExportModal.querySelector("#export__fileserver__instance").value || fsi;

            if (_fsi == null) {
                showNotification("Error", "No FS Instance given!");
                return;
            }

            processingModal.classList.add("active");
            completeModal.classList.remove("active");
            fetch("export_fileserver", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "url": get_format().url,
                    "filename": get_format().filename,
                    "id": fileServerExportModal.querySelector("#export__fileserver__id").value || crypto.randomUUID(),
                    "instance": _fsi
                })
            })
            .then(r => r.json())
            .then(r => {
                completeModal.classList.add("active");
                processingModal.classList.remove("active");
                if (r.success == true) {
                    showNotification("Success", "Successfully exported to FileServer", "green");
                    window.open(r.url);
                } else {
                    showNotification("Error", r.error);
                }
            })
            .catch(e => showNotification("Error", "Failed to export to fileServer!"));
        };
    });
}