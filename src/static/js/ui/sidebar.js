document.getElementById("sidebar-icon").addEventListener("click", closeOpenSidebar);
            
// show sidebar + additional buttons
function closeOpenSidebar() {
    var inputSection = document.querySelector(".input-section");
    var sideMenuButtons = document.querySelector(".side-menu-buttons-container");

    if (inputSection.style.display === "none" || inputSection.style.display === "") {
        inputSection.style.display = "flex";
        sideMenuButtons.style.display = "flex";

        setTimeout(() => {
            inputSection.style.opacity = "1";
            sideMenuButtons.style.opacity = "1";
        }, 200); // for smooth transition
    } else {
        inputSection.style.opacity = "0";
        sideMenuButtons.style.opacity = "0";

        setTimeout(() => {
            inputSection.style.display = "none";
            sideMenuButtons.style.display = "none";
        }, 200); // hide after fade out
    }
}