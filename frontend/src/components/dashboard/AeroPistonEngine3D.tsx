import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import { createAeroPistonEngineModel } from './engineModelBuilder';
import type { BuiltEngineModel, EngineComponentRef } from './engineModelBuilder';
import {
  Eye,
  Flame,
  Layers,
  Zap,
  Maximize2,
  Minimize2,
  Box,
  Activity,
  Play,
  Pause,
  Sliders,
  Plane,
  ShieldAlert,
  Wind,
  Navigation,
  Filter,
} from 'lucide-react';

export type ViewMode = 'REALISTIC' | 'EXPLODED' | 'THERMAL' | 'XRAY' | 'WIREFRAME';
export type HotspotFilterMode = 'ALL' | 'CRITICAL' | 'ALERTS_ONLY';

interface HotspotConfig {
  id: string;
  name: string;
  sensorKey: string;
}

const HOTSPOT_COMPONENTS: HotspotConfig[] = [
  { id: 'propeller', name: '3-Blade Pusher Propeller', sensorKey: 'rpm' },
  { id: 'cylinder_1', name: 'Cylinder #1 (Right Front)', sensorKey: 'cht1' },
  { id: 'cylinder_2', name: 'Cylinder #2 (Right Rear)', sensorKey: 'cht2' },
  { id: 'cylinder_3', name: 'Cylinder #3 (Left Front)', sensorKey: 'cht3' },
  { id: 'cylinder_4', name: 'Cylinder #4 (Left Rear)', sensorKey: 'cht4' },
  { id: 'turbocharger', name: 'Rotax Turbocharger', sensorKey: 'map' },
  { id: 'crankcase', name: 'Oil System & Crankcase', sensorKey: 'oil_pressure' },
  { id: 'exhaust_manifold', name: 'Exhaust Header & Collector', sensorKey: 'egt1' },
];

// Procedural Atmospheric Sky Environment Map (18,500 FT Stratosphere to Horizon Rayleigh Glow)
function createAtmosphericSkyTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d')!;

  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0.0, '#0a1a2f'); // Stratosphere Zenith
  grad.addColorStop(0.3, '#152d4d'); // Upper flight corridor
  grad.addColorStop(0.6, '#284b6f'); // Mid flight level (18,500 ft)
  grad.addColorStop(0.85, '#4f7599'); // Atmospheric horizon Rayleigh glow
  grad.addColorStop(1.0, '#1c2e42'); // Earth/Cloud under-deck
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 512);

  return new THREE.CanvasTexture(canvas);
}

export const AeroPistonEngine3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const { currentFrame } = useDigitalTwinStore();

  // Controls & Display State
  const [viewMode, setViewMode] = useState<ViewMode>('REALISTIC');
  const [explosionFactor, setExplosionFactor] = useState<number>(0.0);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [selectedComponent, setSelectedComponent] = useState<EngineComponentRef | null>(null);
  const [showHotspots, setShowHotspots] = useState<boolean>(true);
  const [hotspotFilter, setHotspotFilter] = useState<HotspotFilterMode>('ALL');
  const [hoveredHotspotId, setHoveredHotspotId] = useState<string | null>(null);

  // Sync state into mutable refs for the 60 FPS animation loop (prevents React re-renders)
  const autoRotateRef = useRef<boolean>(autoRotate);
  autoRotateRef.current = autoRotate;
  const showHotspotsRef = useRef<boolean>(showHotspots);
  showHotspotsRef.current = showHotspots;
  const hotspotFilterRef = useRef<HotspotFilterMode>(hotspotFilter);
  hotspotFilterRef.current = hotspotFilter;
  const hoveredHotspotIdRef = useRef<string | null>(hoveredHotspotId);
  hoveredHotspotIdRef.current = hoveredHotspotId;
  const selectedComponentRef = useRef<EngineComponentRef | null>(selectedComponent);
  selectedComponentRef.current = selectedComponent;

  // Telemetry extraction
  const telemetry = currentFrame?.telemetry;
  const rpm = telemetry?.rpm ?? 2450;
  const cht1 = telemetry?.cht1 ?? telemetry?.cht_C ?? 135;
  const cht2 = telemetry?.cht2 ?? telemetry?.cht_C ?? 138;
  const cht3 = telemetry?.cht3 ?? telemetry?.cht_C ?? 142;
  const cht4 = telemetry?.cht4 ?? telemetry?.cht_C ?? 136;
  const egt1 = telemetry?.egt1 ?? telemetry?.egt_C ?? 740;
  const altitude = telemetry?.altitude_m ?? 5638;

  // System Health & Anomaly State Extraction
  const healthStatus = currentFrame?.health_status ?? 'NOMINAL';
  const isAnomalyDetected = Boolean(
    currentFrame?.anomaly_detection?.is_anomaly ||
    currentFrame?.diagnostic?.anomaly_detected ||
    (healthStatus && healthStatus !== 'NOMINAL' && healthStatus !== 'NORMAL') ||
    (currentFrame?.fault_classification?.predicted_fault && 
     currentFrame.fault_classification.predicted_fault !== 'normal' &&
     currentFrame.fault_classification.predicted_fault !== 'NORMAL')
  );
  const predictedFault = currentFrame?.fault_classification?.predicted_fault ?? currentFrame?.diagnostic?.fault ?? 'normal';
  const faultDisplayName = predictedFault && predictedFault !== 'normal' && predictedFault !== 'NORMAL'
    ? predictedFault.replace(/_/g, ' ').toUpperCase()
    : isAnomalyDetected
    ? 'ANOMALY DETECTED'
    : 'NOMINAL';
  const healthPct = Math.round(
    currentFrame?.degradation_estimation?.estimated_health_pct ??
    (isAnomalyDetected ? 74 : 99)
  );

  // Scene references
  const modelRef = useRef<BuiltEngineModel | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const crankAngleRef = useRef<number>(0);

  // 1. Initialize High-Performance Three.js Environment ONCE on Mount
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    // Scene with dark aerospace environment
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a101f);
    scene.fog = new THREE.FogExp2(0x0a101f, 0.015);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 200);
    camera.position.set(8.8, 6.4, 9.8);
    cameraRef.current = camera;

    // High-performance WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
      precision: 'mediump',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    rendererRef.current = renderer;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Orbit Controls with smooth damping
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxDistance = 40;
    controls.minDistance = 2.0;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // Direct High-Altitude Key Sun Light
    const sunLight = new THREE.DirectionalLight(0xfffbeb, 3.2);
    sunLight.position.set(15, 25, 12);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 1024;
    sunLight.shadow.mapSize.height = 1024;
    scene.add(sunLight);

    // Ambient Aerospace Fill Light
    const skyLight = new THREE.AmbientLight(0xdbeafe, 1.3);
    scene.add(skyLight);

    // Subtle Undercarriage Fill Light
    const groundBounce = new THREE.DirectionalLight(0x475569, 0.8);
    groundBounce.position.set(-10, -10, -5);
    scene.add(groundBounce);

    // Build 3D MALE UAV Aircraft Model
    const engineModel = createAeroPistonEngineModel();
    modelRef.current = engineModel;
    scene.add(engineModel.engineRootGroup);

    // Raycaster for clicking components
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handleCanvasClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(engineModel.engineRootGroup.children, true);

      if (intersects.length > 0) {
        let curr: THREE.Object3D | null = intersects[0].object;
        while (curr && curr.parent && curr.parent !== engineModel.engineRootGroup) {
          curr = curr.parent;
        }
        if (curr) {
          const comp = engineModel.components.get(curr.name);
          if (comp) {
            setSelectedComponent(comp);
          }
        }
      }
    };

    renderer.domElement.addEventListener('pointerdown', handleCanvasClick);

    // Resize handling
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current || !rendererRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      if (w > 0 && h > 0) {
        cameraRef.current.aspect = w / h;
        cameraRef.current.updateProjectionMatrix();
        rendererRef.current.setSize(w, h);
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);
    window.addEventListener('resize', handleResize);

    // 60 FPS Optimized Animation Loop
    let clock = new THREE.Clock();
    const cameraDir = new THREE.Vector3();
    const compWorldOrigin = new THREE.Vector3();
    const compWorldOffset = new THREE.Vector3();
    const toOrigin = new THREE.Vector3();
    const toOffset = new THREE.Vector3();

    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      // Orbit controls
      controls.autoRotate = autoRotateRef.current && !selectedComponentRef.current;
      controls.autoRotateSpeed = 0.8;
      controls.update();

      // Gentle aerodynamic pitch oscillation
      engineModel.engineRootGroup.rotation.z = Math.sin(elapsedTime * 0.5) * 0.015;
      engineModel.engineRootGroup.position.y = Math.sin(elapsedTime * 0.8) * 0.06;

      // Telemetry Kinematics
      const activeFrame = useDigitalTwinStore.getState().currentFrame;
      const activeRpm = activeFrame?.telemetry?.rpm ?? 2450;
      const rps = activeRpm / 60;
      crankAngleRef.current += rps * delta * Math.PI * 2;
      const theta = crankAngleRef.current;

      const { kinematics } = engineModel;

      // Rotate Crankshaft & Pusher Propeller
      kinematics.crankGroup.rotation.z = theta;
      kinematics.propellerGroup.rotation.z = -theta;

      // EO/IR Sensor Turret
      if (kinematics.sensorTurret) {
        kinematics.sensorTurret.rotation.y = Math.sin(elapsedTime * 0.6) * 0.35;
      }

      // Piston Kinematics
      const R = 0.35;
      const L = 1.1;
      kinematics.pistons.forEach((piston) => {
        const angle = theta + piston.phaseAngle;
        const pistonX = piston.sideSign * (R * Math.cos(angle) + Math.sqrt(L * L - R * R * Math.sin(angle) * Math.sin(angle)));
        piston.group.position.x = pistonX;

        const rodAngle = Math.asin((R / L) * Math.sin(angle));
        piston.rodGroup.rotation.z = -piston.sideSign * rodAngle;

        const isNearTDC = Math.abs(Math.sin(angle / 2)) < 0.12;
        if (piston.cylinderIndex < kinematics.sparkLights.length) {
          kinematics.sparkLights[piston.cylinderIndex].intensity = isNearTDC ? 3.0 : 0.0;
        }
      });

      // Direct DOM & SVG Hotspot Overlay Projection (Runs smoothly at 60 FPS without React re-rendering!)
      if (showHotspotsRef.current && containerRef.current && overlayRef.current && svgRef.current) {
        const w = containerRef.current.clientWidth;
        const h = containerRef.current.clientHeight;
        camera.getWorldDirection(cameraDir);

        const currentTelemetry = activeFrame?.telemetry;
        const activeCht1 = currentTelemetry?.cht1 ?? currentTelemetry?.cht_C ?? 135;
        const activeCht2 = currentTelemetry?.cht2 ?? currentTelemetry?.cht_C ?? 138;
        const activeCht3 = currentTelemetry?.cht3 ?? currentTelemetry?.cht_C ?? 142;
        const activeCht4 = currentTelemetry?.cht4 ?? currentTelemetry?.cht_C ?? 136;
        const activeOil = currentTelemetry?.oil_pressure_bar ?? 4.2;
        const activeMap = currentTelemetry?.map ?? 28.5;
        const activeEgt = currentTelemetry?.egt1 ?? currentTelemetry?.egt_C ?? 740;

        HOTSPOT_COMPONENTS.forEach((cfg) => {
          const comp = engineModel.components.get(cfg.id);
          const badgeEl = document.getElementById(`hotspot-badge-${cfg.id}`);
          const valEl = document.getElementById(`hotspot-val-${cfg.id}`);
          const lineEl = document.getElementById(`hotspot-line-${cfg.id}`);
          const reticleEl = document.getElementById(`hotspot-reticle-${cfg.id}`);
          const crossH = document.getElementById(`hotspot-crossh-${cfg.id}`);
          const crossV = document.getElementById(`hotspot-crossv-${cfg.id}`);
          const dotEl = document.getElementById(`hotspot-dot-${cfg.id}`);

          if (!comp || !badgeEl || !lineEl || !reticleEl) return;

          // Component origin in 3D Scene World coordinates
          comp.group.getWorldPosition(compWorldOrigin);

          // Component callout offset relative to stationary aircraft/engine coordinate frame (never spins with rotating prop!)
          compWorldOffset.copy(compWorldOrigin).add(comp.hotspotOffset);

          toOrigin.subVectors(compWorldOrigin, camera.position);
          toOffset.subVectors(compWorldOffset, camera.position);

          const dotOriginVal = cameraDir.dot(toOrigin);
          const dotOffsetVal = cameraDir.dot(toOffset);

          // Value and alert computation
          let valStr = '';
          let isAlert = false;
          if (cfg.sensorKey === 'rpm') valStr = `${Math.round(activeRpm)} RPM`;
          else if (cfg.sensorKey === 'cht1') {
            valStr = `${Math.round(activeCht1)}°C`;
            isAlert = activeCht1 > 175;
          } else if (cfg.sensorKey === 'cht2') {
            valStr = `${Math.round(activeCht2)}°C`;
            isAlert = activeCht2 > 175;
          } else if (cfg.sensorKey === 'cht3') {
            valStr = `${Math.round(activeCht3)}°C`;
            isAlert = activeCht3 > 175;
          } else if (cfg.sensorKey === 'cht4') {
            valStr = `${Math.round(activeCht4)}°C`;
            isAlert = activeCht4 > 175;
          } else if (cfg.sensorKey === 'oil_pressure') {
            valStr = `${activeOil.toFixed(1)} bar`;
            isAlert = activeOil < 2.0;
          } else if (cfg.sensorKey === 'map') {
            valStr = `${activeMap.toFixed(1)} inHg`;
          } else if (cfg.sensorKey === 'egt1') {
            valStr = `${Math.round(activeEgt)}°C`;
            isAlert = activeEgt > 880;
          }

          if (valEl && valEl.textContent !== valStr) {
            valEl.textContent = valStr;
          }

          // Filter check
          let include = true;
          if (hotspotFilterRef.current === 'ALERTS_ONLY' && !isAlert) include = false;
          else if (hotspotFilterRef.current === 'CRITICAL' && !['rpm', 'cht1', 'oil_pressure', 'map'].includes(cfg.sensorKey)) include = false;

          // Camera frustum check
          if (include && dotOriginVal > 0.3 && dotOffsetVal > 0.3) {
            const originNdc = compWorldOrigin.clone().project(camera);
            const offsetNdc = compWorldOffset.clone().project(camera);

            if (
              originNdc.z > -1.0 && originNdc.z < 1.0 &&
              offsetNdc.z > -1.0 && offsetNdc.z < 1.0 &&
              originNdc.x >= -1.25 && originNdc.x <= 1.25 &&
              originNdc.y >= -1.25 && originNdc.y <= 1.25
            ) {
              const originX = (originNdc.x * 0.5 + 0.5) * w;
              const originY = (-(originNdc.y * 0.5) + 0.5) * h;

              const rawBadgeX = (offsetNdc.x * 0.5 + 0.5) * w;
              const rawBadgeY = (-(offsetNdc.y * 0.5) + 0.5) * h;

              const badgeX = Math.max(90, Math.min(w - 90, rawBadgeX));
              const badgeY = Math.max(45, Math.min(h - 50, rawBadgeY));

              const midX = (originX + badgeX) / 2;
              const midY = badgeY;

              // Direct Transform & SVG updates with zero DOM re-creation
              badgeEl.style.transform = `translate3d(${badgeX}px, ${badgeY}px, 0)`;
              badgeEl.style.display = 'block';

              lineEl.setAttribute('points', `${originX},${originY} ${midX},${midY} ${badgeX},${badgeY}`);
              lineEl.setAttribute('display', 'inline');

              reticleEl.setAttribute('cx', originX.toString());
              reticleEl.setAttribute('cy', originY.toString());
              reticleEl.setAttribute('display', 'inline');

              if (crossH) {
                crossH.setAttribute('x1', (originX - 6).toString());
                crossH.setAttribute('y1', originY.toString());
                crossH.setAttribute('x2', (originX + 6).toString());
                crossH.setAttribute('y2', originY.toString());
                crossH.setAttribute('display', 'inline');
              }
              if (crossV) {
                crossV.setAttribute('x1', originX.toString());
                crossV.setAttribute('y1', (originY - 6).toString());
                crossV.setAttribute('x2', originX.toString());
                crossV.setAttribute('y2', (originY + 6).toString());
                crossV.setAttribute('display', 'inline');
              }
              if (dotEl) {
                dotEl.setAttribute('cx', badgeX.toString());
                dotEl.setAttribute('cy', badgeY.toString());
                dotEl.setAttribute('display', 'inline');
              }
              return;
            }
          }

          // Hide elements when culled or filtered
          badgeEl.style.display = 'none';
          lineEl.setAttribute('display', 'none');
          reticleEl.setAttribute('display', 'none');
          if (crossH) crossH.setAttribute('display', 'none');
          if (crossV) crossV.setAttribute('display', 'none');
          if (dotEl) dotEl.setAttribute('display', 'none');
        });
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('pointerdown', handleCanvasClick);
      renderer.dispose();
    };
  }, []);

  // 2. Handle Exploded View Factor
  useEffect(() => {
    if (!modelRef.current) return;
    modelRef.current.components.forEach((comp) => {
      const targetPos = comp.defaultPosition
        .clone()
        .add(comp.explodedDirection.clone().multiplyScalar(explosionFactor * 1.8));
      comp.group.position.copy(targetPos);
    });
  }, [explosionFactor]);

  // 3. View Mode Transitions
  useEffect(() => {
    if (!modelRef.current) return;
    const { components, materials } = modelRef.current;

    components.forEach((comp) => {
      comp.group.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;

          if (viewMode === 'WIREFRAME') {
            mesh.material = materials.wireframe;
          } else if (viewMode === 'XRAY') {
            if (comp.id === 'male_uav_airframe' || comp.id.startsWith('cylinder')) {
              mesh.material = materials.glassXray;
            } else {
              mesh.material = materials.castAluminum;
            }
          } else if (viewMode === 'THERMAL') {
            if (comp.id.startsWith('cylinder')) {
              mesh.material = new THREE.MeshStandardMaterial({
                color: getThermalColor(cht1, 100, 180),
                emissive: getThermalColor(cht1, 100, 180),
                emissiveIntensity: 0.4,
                metalness: 0.7,
              });
            } else if (comp.id === 'exhaust_manifold') {
              mesh.material = new THREE.MeshStandardMaterial({
                color: getThermalColor(egt1, 400, 950),
                emissive: getThermalColor(egt1, 400, 950),
                emissiveIntensity: 0.6,
                metalness: 0.8,
              });
            } else {
              mesh.material = materials.uavPanelDarkSkin;
            }
          } else {
            // REALISTIC Mode matching physical materials
            if (comp.id === 'male_uav_airframe') mesh.material = materials.uavMainPhysicalSkin;
            else if (comp.id === 'crankcase') mesh.material = materials.castAluminum;
            else if (comp.id.startsWith('cylinder')) {
              if (mesh.name.includes('head') || (mesh.geometry && mesh.geometry.type === 'BoxGeometry')) {
                mesh.material = materials.rotaxGreenValve;
              } else {
                mesh.material = materials.castAluminum;
              }
            } else if (comp.id === 'propeller') mesh.material = materials.carbonProp;
            else if (comp.id === 'turbocharger') mesh.material = materials.castAluminum;
            else if (comp.id === 'exhaust_manifold') mesh.material = materials.exhaustHot;
          }
        }
      });
    });
  }, [viewMode, cht1, cht2, cht3, cht4, egt1]);

  const getThermalColor = (temp: number, minT: number, maxT: number): THREE.Color => {
    const ratio = Math.min(Math.max((temp - minT) / (maxT - minT), 0), 1);
    const color = new THREE.Color();
    if (ratio < 0.5) {
      color.setHSL(0.6 - ratio * 0.4, 0.9, 0.45);
    } else {
      color.setHSL(0.15 - (ratio - 0.5) * 0.3, 1.0, 0.5);
    }
    return color;
  };

  // Camera View Presets
  const setCameraPreset = (preset: 'PHOTO_ANGLE' | 'REAR_PUSHER' | 'ENGINE_BAY' | 'FULL_UAV') => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;

    if (preset === 'PHOTO_ANGLE') {
      cam.position.set(8.8, 6.4, 9.8);
      ctrl.target.set(0, 0, 0);
    } else if (preset === 'REAR_PUSHER') {
      cam.position.set(2.8, 1.2, -6.8);
      ctrl.target.set(0, 0.1, -3.9);
    } else if (preset === 'ENGINE_BAY') {
      cam.position.set(3.2, 1.5, -1.2);
      ctrl.target.set(0, 0.1, -1.2);
    } else if (preset === 'FULL_UAV') {
      cam.position.set(0, 14, 12);
      ctrl.target.set(0, 0, 0);
    }
    ctrl.update();
  };

  return (
    <div className="w-full relative">
      <div
        className={`transition-all duration-300 ease-out ${
          isFullscreen
            ? 'fixed inset-0 z-50 rounded-none border-none bg-slate-950 shadow-none'
            : 'relative w-full h-[620px] rounded-xl border border-slate-800 bg-slate-950/90 shadow-2xl overflow-hidden'
        }`}
      >
        {/* 3D WebGL Canvas Container */}
        <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* SVG AVIONICS LEADER LINES OVERLAY (High-Performance Direct DOM updates) */}
        {showHotspots && (
          <svg ref={svgRef} className="absolute inset-0 w-full h-full pointer-events-none z-10 overflow-visible">
            <defs>
              <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.45" />
              </linearGradient>
            </defs>

            {HOTSPOT_COMPONENTS.map((cfg) => (
              <g key={`svg-line-group-${cfg.id}`}>
                {/* 3D Origin Target Circle */}
                <circle
                  id={`hotspot-reticle-${cfg.id}`}
                  cx="0"
                  cy="0"
                  r="9"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                  style={{ display: 'none' }}
                />

                {/* Reticle Crosshair Hairlines */}
                <line
                  id={`hotspot-crossh-${cfg.id}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="0"
                  stroke="#38bdf8"
                  strokeWidth="1"
                  opacity="0.8"
                  style={{ display: 'none' }}
                />
                <line
                  id={`hotspot-crossv-${cfg.id}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="0"
                  stroke="#38bdf8"
                  strokeWidth="1"
                  opacity="0.8"
                  style={{ display: 'none' }}
                />

                {/* Leader Line Path */}
                <polyline
                  id={`hotspot-line-${cfg.id}`}
                  points="0,0 0,0 0,0"
                  fill="none"
                  stroke="url(#lineGrad)"
                  strokeWidth="1.5"
                  strokeDasharray="4 2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ display: 'none' }}
                />

                {/* Terminal Anchor Dot */}
                <circle
                  id={`hotspot-dot-${cfg.id}`}
                  cx="0"
                  cy="0"
                  r="2.5"
                  fill="#06b6d4"
                  style={{ display: 'none' }}
                />
              </g>
            ))}
          </svg>
        )}

        {/* Floating 3D Hotspot Sensor Badges Overlay (Direct Transform Updates at 60 FPS) */}
        {showHotspots && (
          <div ref={overlayRef} className="absolute inset-0 pointer-events-none z-10">
            {HOTSPOT_COMPONENTS.map((cfg) => (
              <div
                key={cfg.id}
                id={`hotspot-badge-${cfg.id}`}
                onMouseEnter={() => setHoveredHotspotId(cfg.id)}
                onMouseLeave={() => setHoveredHotspotId(null)}
                style={{ display: 'none', position: 'absolute', top: 0, left: 0 }}
                className="pointer-events-auto transition-transform duration-75 -translate-x-1/2 -translate-y-1/2"
              >
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg backdrop-blur-md border border-slate-700/80 bg-slate-950/90 text-slate-200 hover:border-cyan-400 shadow-2xl text-[11px] font-mono whitespace-nowrap cursor-pointer hover:scale-105 transition-all">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 shrink-0" />
                  <span className="text-slate-400 font-medium">{cfg.name.split(' (')[0]}:</span>
                  <span id={`hotspot-val-${cfg.id}`} className="font-bold text-cyan-300">
                    --
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Top Header Avionics HUD */}
        <div className="absolute top-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 pointer-events-none z-20">
          <div className="flex items-center gap-3 bg-slate-900/90 backdrop-blur-md px-4 py-2.5 rounded-lg border border-slate-700/70 shadow-2xl pointer-events-auto">
            <div className="w-3 h-3 rounded-full bg-cyan-400 animate-ping" />
            <div>
              <div className="flex items-center gap-2">
                <Plane className="w-4 h-4 text-cyan-400" />
                <h3 className="font-mono text-xs font-bold text-cyan-400 tracking-wider uppercase">
                  MALE UAV PROPULSION DIGITAL TWIN (N190TC)
                </h3>

                {/* Real-Time Nominal vs Anomaly Status Badge */}
                {isAnomalyDetected ? (
                  <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-rose-950/90 text-rose-300 font-mono border border-rose-500/50 font-bold animate-pulse">
                    <ShieldAlert className="w-3 h-3 text-rose-400" />
                    {faultDisplayName} ({healthPct}% HP)
                  </span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono border border-emerald-500/30 font-bold">
                    NOMINAL ({healthPct}% HP)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 text-[11px] text-slate-300 font-mono mt-1">
                <span className="flex items-center gap-1 text-slate-400">
                  <Navigation className="w-3 h-3 text-cyan-400" /> ALT: {Math.round(altitude)} m (18,500 ft)
                </span>
                <span className="flex items-center gap-1 text-slate-400">
                  <Wind className="w-3 h-3 text-emerald-400" /> SPEED: 145 KTS
                </span>
                <span className="text-cyan-400 font-bold">ENGINE: {Math.round(rpm)} RPM</span>
              </div>
            </div>
          </div>

          {/* View Mode Toolbar */}
          <div className="flex items-center gap-1.5 bg-slate-900/90 backdrop-blur-md p-1.5 rounded-lg border border-slate-700/70 shadow-2xl pointer-events-auto">
            <button
              onClick={() => setViewMode('REALISTIC')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                viewMode === 'REALISTIC'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              1:1 Real Drone
            </button>

            <button
              onClick={() => setViewMode('EXPLODED')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                viewMode === 'EXPLODED'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Exploded
            </button>

            <button
              onClick={() => setViewMode('THERMAL')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                viewMode === 'THERMAL'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-500/20 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              Thermal Heat
            </button>

            <button
              onClick={() => setViewMode('XRAY')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                viewMode === 'XRAY'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-500/20 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Eye className="w-3.5 h-3.5 text-emerald-400" />
              Engine Cutaway
            </button>

            <button
              onClick={() => setViewMode('WIREFRAME')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${
                viewMode === 'WIREFRAME'
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm shadow-blue-500/20 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-blue-400" />
              Hologram
            </button>

            <div className="w-px h-5 bg-slate-700 mx-1" />

            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Bottom Control Bar with Hotspot Filter Options */}
        <div className="absolute bottom-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 pointer-events-none z-20">
          {/* Camera Angles Presets */}
          <div className="flex items-center gap-2 bg-slate-900/85 backdrop-blur-md p-1.5 rounded-lg border border-slate-700/60 pointer-events-auto">
            <span className="text-[11px] font-mono text-slate-400 px-2 flex items-center gap-1">
              <Sliders className="w-3 h-3 text-cyan-400" /> Flight View:
            </span>
            <button
              onClick={() => setCameraPreset('PHOTO_ANGLE')}
              className="px-2.5 py-1 text-[11px] font-mono rounded text-cyan-300 bg-cyan-500/20 hover:bg-slate-800 border border-cyan-500/40 font-bold"
            >
              📷 Reference Flight View
            </button>
            <button
              onClick={() => setCameraPreset('REAR_PUSHER')}
              className="px-2.5 py-1 text-[11px] font-mono rounded text-slate-300 hover:bg-slate-800 border border-slate-700/50"
            >
              Rear Pusher Prop
            </button>
            <button
              onClick={() => setCameraPreset('ENGINE_BAY')}
              className="px-2.5 py-1 text-[11px] font-mono rounded text-slate-300 hover:bg-slate-800 border border-slate-700/50"
            >
              Internal Engine Bay
            </button>
            <button
              onClick={() => setCameraPreset('FULL_UAV')}
              className="px-2.5 py-1 text-[11px] font-mono rounded text-slate-300 hover:bg-slate-800 border border-slate-700/50"
            >
              High Altitude Flight
            </button>
          </div>

          {/* Hotspot Filter & Display Controls */}
          <div className="flex items-center gap-3 bg-slate-900/85 backdrop-blur-md px-3.5 py-1.5 rounded-lg border border-slate-700/60 pointer-events-auto">
            {/* Exploded View Slider */}
            {viewMode === 'EXPLODED' && (
              <div className="flex items-center gap-2 font-mono text-xs text-slate-300">
                <span className="text-cyan-400">Expansion:</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={explosionFactor}
                  onChange={(e) => setExplosionFactor(parseFloat(e.target.value))}
                  className="w-24 accent-cyan-400 cursor-pointer"
                />
                <span className="w-8 text-right font-mono text-[11px]">{Math.round(explosionFactor * 100)}%</span>
              </div>
            )}

            {/* Filter Buttons */}
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <Filter className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-slate-400">Hotspots:</span>
              <button
                onClick={() => setHotspotFilter('ALL')}
                className={`px-2 py-1 text-[11px] rounded transition-all ${
                  hotspotFilter === 'ALL' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold' : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                All Metrics
              </button>
              <button
                onClick={() => setHotspotFilter('CRITICAL')}
                className={`px-2 py-1 text-[11px] rounded transition-all ${
                  hotspotFilter === 'CRITICAL' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold' : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                Critical 4
              </button>
              <button
                onClick={() => setHotspotFilter('ALERTS_ONLY')}
                className={`px-2 py-1 text-[11px] rounded transition-all ${
                  hotspotFilter === 'ALERTS_ONLY' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold' : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                Alerts Only
              </button>
            </div>

            <div className="w-px h-5 bg-slate-700 mx-1" />

            {/* Auto Rotation Toggle */}
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono transition-all ${
                autoRotate
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              {autoRotate ? <Pause className="w-3.5 h-3.5 text-emerald-400" /> : <Play className="w-3.5 h-3.5" />}
              Auto Orbit
            </button>

            {/* Hotspots Toggle */}
            <button
              onClick={() => setShowHotspots(!showHotspots)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono transition-all ${
                showHotspots
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              {showHotspots ? 'HUD On' : 'HUD Off'}
            </button>
          </div>
        </div>

        {/* Selected Component Modal Overlay */}
        {selectedComponent && (
          <div className="absolute top-16 right-4 w-80 bg-slate-900/90 backdrop-blur-md border border-cyan-500/40 p-4 rounded-xl shadow-2xl z-30 font-mono text-xs text-slate-200">
            <div className="flex items-center justify-between pb-2 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <Box className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-cyan-300">{selectedComponent.name}</span>
              </div>
              <button
                onClick={() => setSelectedComponent(null)}
                className="text-slate-400 hover:text-slate-100"
              >
                ✕
              </button>
            </div>

            <div className="mt-3 space-y-2 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Callsign:</span>
                <span className="text-slate-200">N190TC / DRDO PS-26054</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Airframe Composite:</span>
                <span className="text-cyan-300 font-bold">Clearcoat Military Epoxy</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Flight Status:</span>
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3 text-emerald-400" /> AIRBORNE NOMINAL
                </span>
              </div>

              {selectedComponent.sensorKey && (
                <div className="mt-2 p-2 bg-slate-800/80 rounded border border-slate-700 text-cyan-300 flex items-center justify-between">
                  <span>Telemetry Metric:</span>
                  <span className="font-bold">
                    {selectedComponent.sensorKey.toUpperCase()}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AeroPistonEngine3D;
