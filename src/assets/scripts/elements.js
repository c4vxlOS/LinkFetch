document.querySelectorAll(".modal").forEach(modal => {
    modal.addEventListener("click", (event) => {
        if (!event.target.classList.contains("modal") && !event.target.hasAttribute("data-modal-close")) return;

        modal.classList.remove("active");
    });
});