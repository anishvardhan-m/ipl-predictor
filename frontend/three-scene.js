// Setup Three.js Scene
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0b0f19, 0.002);

// Camera
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 15;

// Renderer
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Insert canvas into the DOM replacing the spline container or as a new container
const bgContainer = document.querySelector('.spline-bg-container') || document.createElement('div');
if (!bgContainer.classList.contains('spline-bg-container')) {
    bgContainer.className = 'spline-bg-container';
    document.body.insertBefore(bgContainer, document.body.firstChild);
} else {
    bgContainer.innerHTML = ''; // Remove spline
}
bgContainer.appendChild(renderer.domElement);

// --- 1. Procedural Cricket Ball ---
const ballGroup = new THREE.Group();

// Main Ball (Dark Red leather)
const ballGeo = new THREE.SphereGeometry(4, 64, 64);
const ballMat = new THREE.MeshStandardMaterial({
    color: 0x8b0000, 
    roughness: 0.6,
    metalness: 0.1
});
const ball = new THREE.Mesh(ballGeo, ballMat);

// Seam (White prominent threads)
const seamGeo = new THREE.TorusGeometry(4.03, 0.15, 16, 100);
const seamMat = new THREE.MeshStandardMaterial({
    color: 0xfffcf0,
    roughness: 0.9,
    metalness: 0.0
});
const seam = new THREE.Mesh(seamGeo, seamMat);
// Rotate seam to look correct
seam.rotation.y = Math.PI / 4;

ballGroup.add(ball);
ballGroup.add(seam);

// Add slightly offset seam for realism (double seam lines)
const seam2Geo = new THREE.TorusGeometry(4.03, 0.05, 16, 100);
const seam2 = new THREE.Mesh(seam2Geo, seamMat);
seam2.rotation.y = Math.PI / 4;
seam2.position.set(0.1, 0, 0.1); 
ballGroup.add(seam2);

// Position ball to the right side of the screen
ballGroup.position.set(6, 0, -5);
scene.add(ballGroup);


// --- 2. Stadium Lighting ---
const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
scene.add(ambientLight);

// Floodlight 1 (Blueish)
const spotLight1 = new THREE.SpotLight(0x3b82f6, 2);
spotLight1.position.set(15, 20, 10);
spotLight1.angle = Math.PI / 4;
spotLight1.penumbra = 0.5;
scene.add(spotLight1);

// Floodlight 2 (Purple/Reddish)
const spotLight2 = new THREE.SpotLight(0x8b5cf6, 2);
spotLight2.position.set(-15, 20, 10);
spotLight2.angle = Math.PI / 4;
spotLight2.penumbra = 0.5;
scene.add(spotLight2);

// Point light bouncing off the bottom (field reflection)
const pointLight = new THREE.PointLight(0x10b981, 1, 50); // Green glow
pointLight.position.set(0, -10, 5);
scene.add(pointLight);


// --- 3. Stadium Particles (Atmosphere) ---
const particlesGeo = new THREE.BufferGeometry();
const particlesCount = 1500;
const posArray = new Float32Array(particlesCount * 3);

for(let i = 0; i < particlesCount * 3; i++) {
    // Spread particles across a wide 3D area
    posArray[i] = (Math.random() - 0.5) * 60;
}

particlesGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
const particlesMat = new THREE.PointsMaterial({
    size: 0.05,
    color: 0xffffff,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending
});
const particlesMesh = new THREE.Points(particlesGeo, particlesMat);
scene.add(particlesMesh);

// --- Interaction / Mouse follow ---
let mouseX = 0;
let mouseY = 0;
let targetX = 0;
let targetY = 0;

const windowHalfX = window.innerWidth / 2;
const windowHalfY = window.innerHeight / 2;

document.addEventListener('mousemove', (event) => {
    mouseX = (event.clientX - windowHalfX);
    mouseY = (event.clientY - windowHalfY);
});

// --- Animation Loop ---
const clock = new THREE.Clock();

function animate() {
    requestAnimationFrame(animate);
    const elapsedTime = clock.getElapsedTime();

    // Rotate ball slowly
    ballGroup.rotation.y += 0.005;
    ballGroup.rotation.x += 0.002;
    ballGroup.rotation.z += 0.002;

    // Bobbing ball effect
    ballGroup.position.y = Math.sin(elapsedTime * 0.5) * 0.5;

    // Mouse interaction - slightly move camera and ball
    targetX = mouseX * 0.001;
    targetY = mouseY * 0.001;
    
    // Smooth camera pan
    camera.position.x += 0.05 * (targetX - camera.position.x);
    camera.position.y += 0.05 * (-targetY - camera.position.y);
    camera.lookAt(scene.position);

    // Rotate particles slowly
    particlesMesh.rotation.y = elapsedTime * 0.02;

    // Sweep spotlights dynamically
    spotLight1.position.x = 15 * Math.sin(elapsedTime * 0.5);
    spotLight1.position.z = 10 + 5 * Math.cos(elapsedTime * 0.3);
    
    spotLight2.position.x = -15 * Math.cos(elapsedTime * 0.4);

    renderer.render(scene, camera);
}

animate();

// --- Responsive Resize ---
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
});
