// ================= SIDEBAR =================
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) {
        sidebar.classList.toggle("expanded");
    }
}

// ================= MODE SWITCH =================
function switchMode(mode) {
    const manualBtn = document.getElementById("manualBtn");
    const autoBtn = document.getElementById("autoBtn");
    const manualSection = document.getElementById("manualSection");
    const autoSection = document.getElementById("autoSection");

    if (!manualBtn || !autoBtn || !manualSection || !autoSection) {
        console.warn("Mode switch elements not found");
        return;
    }

    if (mode === "manual") {
        manualBtn.classList.add("active");
        autoBtn.classList.remove("active");

        manualSection.classList.remove("hidden");
        autoSection.classList.add("hidden");
    } else {
        autoBtn.classList.add("active");
        manualBtn.classList.remove("active");

        autoSection.classList.remove("hidden");
        manualSection.classList.add("hidden");
    }
}

// ================= GEO TRACKING =================
let startPosition = null;

function startTrip() {
    const vehicle = document.getElementById("autoVehicle").value;
    const status = document.getElementById("tripStatus");

    if (!navigator.geolocation) {
        alert("Geolocation not supported");
        return;
    }

    status.innerText = "Starting trip...";

    navigator.geolocation.getCurrentPosition(pos => {
        startPosition = pos.coords;

        fetch("/start-trip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lat: startPosition.latitude,
                lon: startPosition.longitude,
                vehicle: vehicle
            })
        });

        document.getElementById("startTripBtn").classList.add("hidden");
        document.getElementById("endTripBtn").classList.remove("hidden");

        status.innerText = "Trip started. Tracking...";
    });
}

function endTrip() {
    const vehicle = document.getElementById("autoVehicle").value;
    const status = document.getElementById("tripStatus");

    navigator.geolocation.getCurrentPosition(pos => {
        fetch("/end-trip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lat: pos.coords.latitude,
                lon: pos.coords.longitude,
                vehicle: vehicle
            })
        })
        .then(res => res.json())
        .then(data => {
            status.innerText = `Trip ended. Distance: ${data.distance} km`;
            window.location.reload();
        });
    });
}
