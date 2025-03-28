const dropArea = document.querySelector(".drop_box"),
  button = dropArea.querySelector("button"),
  dragText = dropArea.querySelector("header"),
  input = dropArea.querySelector("input");
let file;
var filename;

//button.onclick = () => {
//  input.click();
//};
//
//input.addEventListener("change", function (e) {
//  var fileName = e.target.files[0].name;
//  let filedata = `
//    <form action="" method="post">
//    <div class="form">
//    <h4>${fileName}</h4>
//    <input type="email" placeholder="Enter email upload file">
//    <button class="btn">Upload</button>
//    </div>
//    </form>`;
//  dropArea.innerHTML = filedata;
//});

   document.getElementById("fileID").addEventListener("change", function() {
        if (this.files.length > 0) {
            document.getElementById("submitBtn").click();  // Submit the form after a file is selected
        }
    });

  document
  .getElementById("fileID")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    // Create a FormData object to combine both forms' data
    var formData = new FormData(document.getElementById("form"));
    formData.forEach((value, key) => {
    console.log(key, value);
});
    console.log("omoo");

    // Submit the combined form data via POST
    fetch("/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (response.redirected) {
          // Redirect manually using the URL from the response
          window.location.href = response.url;
        } else {
          return response.json(); // For error handling or any other response
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });
