// tutorial shown on "?" button click

document.getElementById("info-button").addEventListener("click", showHidePopupTutorial);
document.getElementById("hideTutorial-button").addEventListener("click", closePopupTutorial);

function showHidePopupTutorial() {
    var popup = document.getElementById("tutorialPopup")

    if (popup.style.display === "none" || popup.style.display === "") {
        popup.style.display = "flex";

        setTimeout(() => {
            popup.style.opacity = "1";
        }, 200); // for smooth transition
    } else {
        popup.style.opacity = "0";

        setTimeout(() => {
            popup.style.display = "none";
        }, 200); // hide after fade out
    }
}

function closePopupTutorial () {
    var popup = document.getElementById("tutorialPopup")

    if (popup.style.display === "flex") {
        popup.style.display = "none";

        setTimeout(() => {
            popup.style.opacity = "0";
        }, 200); // for smooth transition
    }
}