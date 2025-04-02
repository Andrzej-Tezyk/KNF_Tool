const toggleBottomPanelBtn = document.getElementById('toggleBottomPanelBtn');

document.getElementById("file-button").addEventListener("click", toggleBottomPanel);
document.getElementById("hidePanel-button").addEventListener("click", toggleBottomPanel);
document.getElementById("selectAllBtn").addEventListener("click", selectAllFiles);
document.getElementById("uncheckAllBtn").addEventListener("click", uncheckAllFiles);

// show/hide panel with document checkboxes
function toggleBottomPanel() {
    const panel = document.getElementById("bottom-panel");
    if (panel.style.bottom === "0px") {
        panel.style.bottom = "-100%";
    } else {
        panel.style.bottom = "0px";
    }
}

// close bottom tab on Esc
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const panel = document.getElementById("bottom-panel");
        if (panel && panel.style.bottom === "0px") { // check if the panel is open
            toggleBottomPanel();
        }
    }
});

// buttons on bottom panel
function selectAllFiles() {
    const checkboxes = document.querySelectorAll(".file-checkbox"); // select all checkboxes inside the scrollable list
    checkboxes.forEach(checkbox => {
        checkbox.checked = true; // all checkboxes are checked
    });
    updateSelectedFilesDisplay(); // update choosen files
}

function uncheckAllFiles() {
    const checkboxes = document.querySelectorAll(".file-checkbox"); // select all checkboxes inside the scrollable list
    checkboxes.forEach(checkbox => {
        checkbox.checked = false; // all checkboxes are checked
    });
    updateSelectedFilesDisplay(); // update choosen files
}



// document checkboxes listener
document.querySelectorAll('.file-checkbox').forEach((checkbox) => { // eventlisteners for all file checkboxes
    checkbox.addEventListener('change', updateSelectedFilesDisplay);
});        



// show shorten filenames under input textfield
function updateSelectedFilesDisplay() {
    const selectedFilesContainer = document.getElementById('selected-files');

    if (selectedFilesContainer) {
        let selectedFiles = [];

        document.querySelectorAll('.file-checkbox:checked').forEach((checkbox) => {
            let fullName = checkbox.value;
            let shortName = fullName.length > 15 && fullName.includes('_') 
                            ? fullName.slice(11, 25) 
                            : fullName;
            selectedFiles.push(shortName);
        });

        if (selectedFiles.length > 0) {
            selectedFilesContainer.textContent = selectedFiles.join(', ');
            selectedFilesContainer.style.color = ''; // reset to default text color
        } else {
            selectedFilesContainer.textContent = "No file selected";
            selectedFilesContainer.style.color = 'red'; // show red warning text
        }
    }
}

// call once to initialize state correctly
updateSelectedFilesDisplay();