function validateForm() {
    const role = document.getElementById('role').value;
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const errorMessage = document.getElementById('error-message');

    if (role === "" || username === "" || password === "") {
        errorMessage.textContent = "All fields (Role, Username, and Password) are required.";
        errorMessage.style.display = "block";
        return false; // Prevent form submission
    }

    // Clear error message if validation passes
    errorMessage.style.display = "none";
    return true; 
}