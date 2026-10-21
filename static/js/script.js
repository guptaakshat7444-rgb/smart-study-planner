// Delete Alerts

document.addEventListener("DOMContentLoaded", () => {
    const deleteButtons = document.querySelectorAll(".delete-btn");

    deleteButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
            const confirmed = confirm(
                "Are you sure you want to delete this item?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});


// Availability Form Validation


document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("availability-form");

    if (!form) {
        return;
    }

    const dateInput = document.getElementById("available_date");
    const hoursInput = document.getElementById("available_hours");
    const startInput = document.getElementById("start_time");
    const endInput = document.getElementById("end_time");

    // Prevent selecting a date in the past.
    const today = new Date();
    const localDate = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    dateInput.min = localDate;

    form.addEventListener("submit", (event) => {
        const selectedDate = dateInput.value;
        const hours = Number(hoursInput.value);
        const startTime = startInput.value;
        const endTime = endInput.value;

        if (selectedDate < localDate) {
            event.preventDefault();
            alert("Please select today or a future date.");
            return;
        }

        if (!Number.isFinite(hours) || hours <= 0) {
            event.preventDefault();
            alert("Available hours must be greater than zero.");
            return;
        }

        if (hours > 24) {
            event.preventDefault();
            alert("Available hours cannot exceed 24 hours.");
            return;
        }

        if (startTime && endTime && endTime <= startTime) {
            event.preventDefault();
            alert("End time must be later than start time.");
        }
    });
});


