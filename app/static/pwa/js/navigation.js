function navigate(url) {
    fetch(url)
        .then(res => res.text())
        .then(html => {
            document.getElementById("content").innerHTML = html;
        })
        .catch(err => {
            document.getElementById("content").innerHTML =
                "<p>Fehler beim Laden des Moduls.</p>";
        });
}
