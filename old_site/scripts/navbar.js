//navbar.js
export function loadNavbar() {
  fetch("navbar.html")
    .then(res => res.text())
    .then(html => {
      document.body.insertAdjacentHTML("afterbegin", html);

      // After inserting, adjust login/logout link
      const currentUser = JSON.parse(localStorage.getItem("currentUser"));
      const loginLink = document.getElementById("login-link");

      if (!currentUser) {
        // redirect if on index and not logged in
        if (window.location.pathname.endsWith("index.html")) {
          window.location.href = "login.html";
        }
      } else {
        loginLink.textContent = "Logout";
        loginLink.addEventListener("click", e => {
          e.preventDefault();
          localStorage.clear();
          window.location.href = "login.html";
        });
      }
    });
}
