import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { createFly } from "./FlyModel";

type StoryState = {
  state: string;
  cycle: number;
  current_item?: string;
  selected_strategy?: string;
  last_action: string;
  simulated_time?: string;
  solar_intensity?: number;
  caffeine_level?: number;
};

const SLEEP_STATES = new Set(["PREPARE_SLEEP", "SLEEP", "DREAM", "CONSOLIDATE_MEMORY", "WAKE_AGAIN"]);
const DSA_STATES = new Set(["SOLVE_DSA", "TEST_SOLUTION", "DEBUG_SOLUTION"]);
const JOB_STATES = new Set(["SEARCH_JOBS", "EVALUATE_JOB", "DRAFT_APPLICATION", "WAITING_FOR_HUMAN_APPROVAL"]);
const COFFEE_STATES = new Set(["COFFEE_BREAK"]);

function box(width: number, height: number, depth: number, color: number) {
  return new THREE.Mesh(
    new THREE.BoxGeometry(width, height, depth),
    new THREE.MeshStandardMaterial({ color, roughness: 0.72 }),
  );
}

function screenTexture(kind: "dsa" | "jobs") {
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 460;
  const ctx = canvas.getContext("2d")!;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  return { kind, canvas, ctx, texture };
}

function drawDsaScreen(
  target: ReturnType<typeof screenTexture>,
  state: StoryState,
) {
  const { ctx, canvas } = target;
  const w = canvas.width;
  ctx.fillStyle = "#08100c";
  ctx.fillRect(0, 0, w, canvas.height);
  ctx.fillStyle = "#22372b";
  ctx.fillRect(0, 0, w, 54);
  ctx.fillStyle = "#e8ad4d";
  ctx.font = "bold 22px monospace";
  ctx.fillText("ALGO BAY / DSA-01", 28, 36);
  ctx.fillStyle = "#8fcf79";
  ctx.font = "18px monospace";
  ctx.fillText(state.current_item || "Pair With Target Sum", 30, 96);
  ctx.fillStyle = "#b9c5bb";
  ctx.font = "15px monospace";
  [
    "strategy: " + (state.selected_strategy || "selecting..."),
    "seen = {}",
    "for index, value in enumerate(nums):",
    "    wanted = target - value",
    "    if wanted in seen: return [seen[wanted], index]",
  ].forEach((line, index) => ctx.fillText(line, 32, 145 + index * 34));
  ctx.fillStyle = "#16251d";
  ctx.fillRect(30, 330, w - 60, 94);
  ctx.fillStyle = state.state === "DEBUG_SOLUTION" ? "#d67b84" : "#8fcf79";
  ctx.font = "bold 18px monospace";
  ctx.fillText(
    state.state === "DEBUG_SOLUTION" ? "● DEBUGGING · BOUNDED 2/3" : "● TEST SANDBOX · READY",
    52,
    366,
  );
  ctx.fillStyle = "#829083";
  ctx.font = "13px monospace";
  ctx.fillText("public 2/2  hidden protected  network OFF", 52, 400);
  target.texture.needsUpdate = true;
}

function drawJobsScreen(
  target: ReturnType<typeof screenTexture>,
  state: StoryState,
) {
  const { ctx, canvas } = target;
  const w = canvas.width;
  ctx.fillStyle = "#f3f5f7";
  ctx.fillRect(0, 0, w, canvas.height);
  ctx.fillStyle = "#0a66c2";
  ctx.fillRect(0, 0, w, 62);
  ctx.fillStyle = "white";
  ctx.font = "bold 27px sans-serif";
  ctx.fillText("in", 24, 41);
  ctx.font = "bold 20px sans-serif";
  ctx.fillText("Internship Draft Studio", 70, 38);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(24, 86, 210, 334);
  ctx.fillStyle = "#dce6f1";
  ctx.beginPath();
  ctx.arc(128, 142, 36, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#243342";
  ctx.font = "bold 18px sans-serif";
  ctx.fillText("I. Fly", 96, 202);
  ctx.fillStyle = "#596b7b";
  ctx.font = "14px sans-serif";
  ctx.fillText("Aspiring tiny engineer", 57, 229);
  ctx.fillText("Python · DSA · APIs", 65, 258);
  ctx.fillStyle = "#fff";
  ctx.fillRect(256, 86, 486, 146);
  ctx.fillStyle = "#253746";
  ctx.font = "bold 21px sans-serif";
  ctx.fillText("Software Engineering Intern", 280, 122);
  ctx.fillStyle = "#0a66c2";
  ctx.font = "bold 16px sans-serif";
  ctx.fillText("ByteBramble Labs · Fictional", 280, 154);
  ctx.fillStyle = "#5b6873";
  ctx.font = "14px sans-serif";
  ctx.fillText("Remote · 96% match · Evidence checked", 280, 184);
  ctx.fillStyle = "#e8f2fb";
  ctx.fillRect(256, 250, 486, 170);
  ctx.fillStyle = "#184d7e";
  ctx.font = "bold 15px sans-serif";
  ctx.fillText(state.state.replaceAll("_", " "), 280, 286);
  ctx.fillStyle = "#43586b";
  ctx.font = "14px sans-serif";
  ctx.fillText("Local truthful draft prepared.", 280, 326);
  ctx.fillText("No scraping. No auto-submit.", 280, 354);
  ctx.fillStyle = "#0a66c2";
  ctx.fillRect(280, 374, 220, 30);
  ctx.fillStyle = "white";
  ctx.font = "bold 12px sans-serif";
  ctx.fillText("AWAITING HUMAN APPROVAL", 302, 394);
  target.texture.needsUpdate = true;
}

function makeMonitor(texture: THREE.Texture, accent: number) {
  const group = new THREE.Group();
  const frame = box(3.45, 2.2, 0.22, 0x242824);
  frame.position.y = 2.4;
  group.add(frame);
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(3.12, 1.85),
    new THREE.MeshBasicMaterial({ map: texture, toneMapped: false }),
  );
  screen.position.set(0, 2.42, 0.121);
  group.add(screen);
  const stand = box(0.24, 0.85, 0.24, 0x30342f);
  stand.position.y = 1.05;
  group.add(stand);
  const base = box(1.25, 0.12, 0.78, accent);
  base.position.y = 0.61;
  group.add(base);
  return group;
}


export default function StoryWorld({ state }: { state: StoryState }) {
  const [view, setView] = useState<"room" | "fly">("room");
  const viewRef = useRef(view);
  viewRef.current = view;
  const mountRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111c29);
    scene.fog = new THREE.Fog(0x111c29, 28, 55);
    const camera = new THREE.PerspectiveCamera(46, mount.clientWidth / mount.clientHeight, 0.1, 100);
    camera.position.set(12, 12, 20);
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.5, 0);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI * 0.48;
    controls.minDistance = 7;
    controls.maxDistance = 28;

    const ambientLight = new THREE.HemisphereLight(0xaecad1, 0x2b2419, 1.5);
    scene.add(ambientLight);
    const keyLight = new THREE.DirectionalLight(0xffe1a6, 2.2);
    keyLight.position.set(2, 9, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.left = -14; keyLight.shadow.camera.right = 14;
    keyLight.shadow.camera.top = 14; keyLight.shadow.camera.bottom = -14;
    keyLight.shadow.normalBias = .035;
    scene.add(keyLight);
    const dsaGlow = new THREE.PointLight(0x6fbf83, 2.3, 9);
    dsaGlow.position.set(-4.5, 3, 1);
    scene.add(dsaGlow);
    const jobsGlow = new THREE.PointLight(0x0a66c2, 2.2, 9);
    jobsGlow.position.set(5, 3, 1);
    scene.add(jobsGlow);
    const sunlight = new THREE.PointLight(0xffd991, 4.0, 22);
    sunlight.position.set(0, 5.0, -4.8);
    scene.add(sunlight);
    const specimenLight = new THREE.PointLight(0xdcefff, 0, 9, 1.5);
    scene.add(specimenLight);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(22, 16),
      new THREE.MeshStandardMaterial({ color: 0x6c6152, roughness: 0.84 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);
    const backWall = box(22, 8, 0.25, 0x46596a);
    backWall.position.set(0, 4, -6);
    scene.add(backWall);
    // Floorboard seams, wall trim and a woven-looking rug ground the room.
    for (let x = -10; x <= 10; x += 1.1) {
      const seam = box(.022, .009, 16, 0x423d36); seam.position.set(x, .01, 0); scene.add(seam);
    }
    const trim = box(22, .2, .13, 0x8d9b9b); trim.position.set(0, .2, -5.82); scene.add(trim);
    const rug = box(10.8, .025, 5.2, 0x354f59); rug.position.set(.1, .03, 2.5); rug.receiveShadow = true; scene.add(rug);
    for (let i = 0; i < 13; i++) { const stitch = box(10.4, .004, .024, 0x637977); stitch.position.set(.1, .045, .1 + i * .39); scene.add(stitch); }
    const shelf = box(4.3, .15, .75, 0x96765a); shelf.position.set(6.6, 5.4, -5.4); scene.add(shelf);
    [0x9bb58c, 0xb38072, 0xd4b784, 0x718fab, 0xb1a3bd].forEach((color, i) => {
      const book = box(.38, .8 + (i % 3) * .13, .5, color); book.position.set(5.15 + i * .46, 5.95, -5.35); book.rotation.z = i === 4 ? -.14 : 0; scene.add(book);
    });

    const bed = new THREE.Group();
    const frame = box(5.1, 0.48, 3.45, 0x46392b);
    frame.position.y = 0.43;
    bed.add(frame);
    const mattress = box(4.85, 0.48, 3.18, 0xc8c1aa);
    mattress.position.y = 0.86;
    bed.add(mattress);
    const blanket = box(3.0, 0.12, 3.2, 0x536f65);
    blanket.position.set(-0.72, 1.15, 0);
    bed.add(blanket);
    const pillow = box(1.15, 0.22, 1.45, 0xe4ddc9);
    pillow.position.set(1.62, 1.19, 0);
    bed.add(pillow);
    bed.position.set(-6.9, 0, -2.8);
    scene.add(bed);

    const skyMaterial = new THREE.MeshBasicMaterial({ color: 0x7eb7ca });
    const windowFrame = box(5.0, 3.2, 0.18, 0x363b35);
    windowFrame.position.set(0, 4.45, -5.76);
    scene.add(windowFrame);
    const sky = new THREE.Mesh(new THREE.PlaneGeometry(4.55, 2.75), skyMaterial);
    sky.position.set(0, 4.45, -5.65);
    scene.add(sky);
    const sun = new THREE.Mesh(
      new THREE.SphereGeometry(0.32, 20, 14),
      new THREE.MeshBasicMaterial({ color: 0xffd36a }),
    );
    const moon = new THREE.Mesh(
      new THREE.SphereGeometry(0.26, 20, 14),
      new THREE.MeshBasicMaterial({ color: 0xd8e5ee }),
    );
    scene.add(sun, moon);
    const mullionV = box(0.12, 3.0, 0.2, 0x363b35);
    mullionV.position.set(0, 4.45, -5.5);
    scene.add(mullionV);
    const mullionH = box(4.7, 0.12, 0.2, 0x363b35);
    mullionH.position.set(0, 4.45, -5.5);
    scene.add(mullionH);

    const dsaTexture = screenTexture("dsa");
    const jobsTexture = screenTexture("jobs");
    drawDsaScreen(dsaTexture, stateRef.current);
    drawJobsScreen(jobsTexture, stateRef.current);
    const dsaDesk = box(5.0, 0.32, 2.4, 0x4a3a29);
    dsaDesk.position.set(-4.0, 1.2, 2.1);
    scene.add(dsaDesk);
    const jobDesk = box(5.0, 0.32, 2.4, 0x4a3a29);
    jobDesk.position.set(4.6, 1.2, 2.1);
    scene.add(jobDesk);
    const dsaMonitor = makeMonitor(dsaTexture.texture, 0x3c6846);
    dsaMonitor.position.set(-4.0, 1.15, 1.8);
    scene.add(dsaMonitor);
    const jobMonitor = makeMonitor(jobsTexture.texture, 0x0a66c2);
    jobMonitor.position.set(4.6, 1.15, 1.8);
    scene.add(jobMonitor);
    [-4, 4.6].forEach(x => {
      const keyboard = box(2.25, .1, .74, 0x252f37); keyboard.position.set(x, 1.43, 2.75); scene.add(keyboard);
      for (let row = 0; row < 4; row++) for (let col = 0; col < 12; col++) {
        const key = box(.14, .045, .105, col % 5 === 0 ? 0x7a989f : 0x617079);
        key.position.set(x - .94 + col * .17, 1.505, 2.48 + row * .16); scene.add(key);
      }
      const mouse = new THREE.Mesh(new THREE.SphereGeometry(.19, 18, 12), new THREE.MeshStandardMaterial({ color: 0x9aabb0, roughness: .5 }));
      mouse.scale.set(.8, .35, 1.3); mouse.position.set(x + 1.5, 1.43, 2.7); scene.add(mouse);
      const chair = box(1.3, .18, 1.1, 0x334252); chair.position.set(x, .84, 4.2); scene.add(chair);
      const chairBack = box(1.3, 1.2, .17, 0x334252); chairBack.position.set(x, 1.46, 4.7); scene.add(chairBack);
      const stem = box(.12, .8, .12, 0x8e9899); stem.position.set(x, .4, 4.2); scene.add(stem);
    });
    [-5.8, -2.2, 2.8, 6.4].forEach((x) => {
      const leg = box(0.22, 1.2, 0.22, 0x2a2923);
      leg.position.set(x, 0.58, 2.1);
      scene.add(leg);
    });

    // Coffee station: deliberately fictional, with visible brain-state feedback.
    const coffeeCounter = box(2.8, 1.25, 1.5, 0x5a412d);
    coffeeCounter.position.set(0.2, 0.62, 3.85);
    scene.add(coffeeCounter);
    const machine = box(0.95, 1.15, 0.72, 0x282b29);
    machine.position.set(-0.35, 1.75, 3.85);
    scene.add(machine);
    const machinePanel = new THREE.Mesh(
      new THREE.PlaneGeometry(0.62, 0.28),
      new THREE.MeshBasicMaterial({ color: 0xe8ad4d }),
    );
    machinePanel.position.set(-0.35, 1.94, 4.22);
    scene.add(machinePanel);
    const cup = new THREE.Mesh(
      new THREE.CylinderGeometry(0.22, 0.18, 0.42, 18),
      new THREE.MeshStandardMaterial({ color: 0xe4ddc9, roughness: 0.72 }),
    );
    cup.position.set(0.55, 1.48, 3.86);
    scene.add(cup);
    const coffee = new THREE.Mesh(
      new THREE.CircleGeometry(0.18, 18),
      new THREE.MeshBasicMaterial({ color: 0x28160b }),
    );
    coffee.rotation.x = -Math.PI / 2;
    coffee.position.set(0.55, 1.695, 3.86);
    scene.add(coffee);
    const caffeineLight = new THREE.PointLight(0xe8ad4d, 0.0, 6);
    caffeineLight.position.set(0.2, 2.3, 3.5);
    scene.add(caffeineLight);

    const fly = createFly();
    fly.position.set(-6.1, 1.7, -2.8);
    scene.add(fly);
    scene.traverse(object => { if (object instanceof THREE.Mesh && !(object.material instanceof THREE.MeshBasicMaterial)) { object.castShadow = true; object.receiveShadow = true; } });
    const targets = {
      bed: new THREE.Vector3(-6.1, 1.7, -2.8),
      dsa: new THREE.Vector3(-3.7, 2.0, 3.55),
      jobs: new THREE.Vector3(4.9, 2.0, 3.55),
      coffee: new THREE.Vector3(0.55, 2.05, 3.35),
      middle: new THREE.Vector3(0, 2.6, 0.6),
    };

    const clock = new THREE.Clock();
    let disposed = false;
    let lastState = "";
    let lastView = "room";
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const animate = () => {
      if (disposed) return;
      requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();
      const current = stateRef.current;
      const sleeping = SLEEP_STATES.has(current.state);
      const target = sleeping
        ? targets.bed
        : DSA_STATES.has(current.state)
          ? targets.dsa
          : JOB_STATES.has(current.state)
            ? targets.jobs
            : COFFEE_STATES.has(current.state)
              ? targets.coffee
            : targets.middle;
      const moving = fly.position.distanceTo(target) > .2;
      fly.position.lerp(target, reducedMotion.matches ? 1 : 0.035);
      fly.rotation.z = THREE.MathUtils.lerp(fly.rotation.z, sleeping ? -.23 : COFFEE_STATES.has(current.state) ? -.3 : 0, .06);
      fly.rotation.y = THREE.MathUtils.lerp(fly.rotation.y, sleeping ? .2 : Math.PI / 2, .04);
      fly.children.filter((child) => child.name === "wing").forEach((wing, index) => {
        wing.rotation.x = sleeping || reducedMotion.matches ? .12 * wing.userData.side : Math.sin(elapsed * (moving ? 48 : 8) + index) * (moving ? .55 : .035);
      });
      fly.children.filter(child => child.name === "leg").forEach(leg => {
        leg.rotation.z = sleeping || reducedMotion.matches ? 0 : Math.sin(elapsed * (moving ? 10 : 6) + leg.userData.ordinal * 2 + leg.userData.side) * (moving ? .15 : .04);
      });
      if (viewRef.current === "fly") {
        controls.enabled = false;
        camera.position.lerp(fly.position.clone().add(new THREE.Vector3(2.8, 2.1, 3.6)), .065);
        controls.target.lerp(fly.position, .1);
      } else if (lastView === "fly") {
        camera.position.set(12, 12, 20); controls.target.set(0, 1.5, 0); controls.enabled = true;
      }
      specimenLight.position.copy(fly.position).add(new THREE.Vector3(1.5, 2, 1.8));
      specimenLight.intensity = viewRef.current === "fly" ? 5 : 0;
      lastView = viewRef.current;

      const parts = (current.simulated_time || "12:00").split(":").map(Number);
      const simulatedMinutes = parts[0] * 60 + parts[1];
      const daylight = current.solar_intensity || 0;
      const solarPhase = Math.max(0, Math.min(1, (simulatedMinutes - 390) / 720));
      const sunX = Math.cos(Math.PI - solarPhase * Math.PI) * 1.65;
      const sunY = 4.05 + Math.sin(solarPhase * Math.PI) * 1.18;
      skyMaterial.color.setRGB(
        0.025 + daylight * 0.43,
        0.04 + daylight * 0.61,
        0.095 + daylight * 0.69,
      );
      sun.position.set(sunX, sunY, -5.52);
      moon.position.set(
        -sunX,
        4.1 + Math.max(0, 1 - daylight) * 0.85,
        -5.51,
      );
      sun.visible = simulatedMinutes >= 390 && simulatedMinutes <= 1110;
      moon.visible = !sun.visible || daylight < 0.22;
      keyLight.intensity = 0.22 + daylight * 3.3;
      ambientLight.intensity = 0.75 + daylight * 1.8;
      sunlight.intensity = daylight * 6.0;
      renderer.toneMappingExposure = 0.9 + daylight * 0.25;
      const caffeine = (current.caffeine_level || 0) / 100;
      caffeineLight.intensity = 0.25 + caffeine * 4.5;
      caffeineLight.color.set(caffeine > 0.75 ? 0xff9356 : 0xe8ad4d);
      const signature = current.state + ":" + current.current_item + ":" + current.selected_strategy;
      if (signature !== lastState) {
        drawDsaScreen(dsaTexture, current);
        drawJobsScreen(jobsTexture, current);
        lastState = signature;
      }
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const resize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    return () => {
      disposed = true;
      observer.disconnect();
      controls.dispose();
      dsaTexture.texture.dispose();
      jobsTexture.texture.dispose();
      renderer.dispose();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh) { object.geometry.dispose(); (Array.isArray(object.material) ? object.material : [object.material]).forEach(material => material.dispose()); }
      });
      renderer.domElement.remove();
    };
  }, []);

  return (
    <div className="story-world" ref={mountRef} aria-label="Interactive 3D room. Drag to orbit and scroll to zoom.">
      <div className="world-hud">
        <span>01 / THE OBSERVATION ROOM</span>
        <b>{state.state.replaceAll("_", " ")}</b>
        <em>{state.simulated_time || "--:--"} · {Math.round((state.solar_intensity || 0) * 100)}% SUN</em>
      </div>
      <div className="camera-controls" aria-label="Camera view"><button aria-pressed={view === "room"} onClick={() => setView("room")}>Room view</button><button aria-pressed={view === "fly"} onClick={() => setView("fly")}>Follow fly ↗</button></div>
      <div className="camera-hint">{view === "room" ? "Drag to orbit · scroll to zoom" : "Live specimen view · illustrated anatomy"}</div>
      <div className="room-legend" aria-hidden="true">
        <span><i className="bed-dot" />REST POD</span>
        <span><i className="dsa-dot" />DSA BAY</span>
        <span><i className="jobs-dot" />APPLICATION DESK</span>
        <span><i className="coffee-dot" />CAFFEINE STATION</span>
      </div>
    </div>
  );
}
