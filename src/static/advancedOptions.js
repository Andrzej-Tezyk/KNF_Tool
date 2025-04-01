// advanced options elements
var checkBox = document.getElementById("change_lebgth");
var select = document.getElementById("words-sentence-select");
var text = document.getElementById("select-text");

select.style.display = "none";
text.style.display = "none";

checkBox.addEventListener("change", function () {
select.style.display = checkBox.checked ? "block" : "none";
text.style.display = checkBox.checked ? "block" : "none";
});

var slider = document.getElementById("myRange");
var output = document.getElementById("demo");
output.innerHTML = slider.value;

slider.oninput = function() {
output.innerHTML = this.value;
}

function openForm() {
    document.getElementById("tempInfo").style.display = "block";
}

function closeForm() {
    document.getElementById("tempInfo").style.display = "none";
}

var openButton = document.querySelector(".open-button");
var closeButton = document.querySelector(".btn.cancel");
var tempInfo = document.getElementById("tempInfo");

openButton.addEventListener("click", function () {
    tempInfo.style.display = "block";
});

closeButton.addEventListener("click", function () {
    tempInfo.style.display = "none";
});