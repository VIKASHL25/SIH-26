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

export interface HotspotProjection {
  id: string;
  name: string;
  val: string;
  originX: number;
  originY: number;
  badgeX: number;
  badgeY: number;
  alert: boolean;
  isHovered: boolean;
}

export const AeroPistonEngine3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
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

  // Engine Telemetry Extraction from currentFrame
  const telemetry = currentFrame?.telemetry;
  const rpm = telemetry?.rpm ?? 2450;
  const cht1 = telemetry?.cht1 ?? telemetry?.cht_C ?? 135;
  const cht2 = telemetry?.cht2 ?? telemetry?.cht_C ?? 138;
  const cht3 = telemetry?.cht3 ?? telemetry?.cht_C ?? 142;
  const cht4 = telemetry?.cht4 ?? telemetry?.cht_C ?? 136;
  const egt1 = telemetry?.egt1 ?? telemetry?.egt_C ?? 740;
  const oilPressure = telemetry?.oil_pressure_bar ?? 4.2;
  const map = telemetry?.map ?? 28.5;
  const altitude = telemetry?.altitude_m ?? 5638;

  // Scene references
  const modelRef = useRef<BuiltEngineModel | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const crankAngleRef = useRef<number>(0);
  const cloudsGroupRef = useRef<THREE.Group | null>(null);

  // Hotspot Screen Projections State with Avionics Leader Lines
  const [hotspotPositions, setHotspotPositions] = useState<HotspotProjection[]>([]);

  // 1. Initialize Three.js Sky Atmosphere Environment, Photorealistic Lighting & Orbit Controls
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x7389a2);
    scene.fog = new THREE.FogExp2(0x7389a2, 0.012);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 200);
    camera.position.set(8.8, 6.4, 9.8);
    cameraRef.current = camera;

    // WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;

    // Clear canvas
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxDistance = 40;
    controls.minDistance = 2.0;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // Direct High-Altitude Sunlight
    const sunLight = new THREE.DirectionalLight(0xfffbeb, 3.0);
    sunLight.position.set(15, 25, 12);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    scene.add(sunLight);

    // Ambient Sky Environment Fill Light
    const skyLight = new THREE.AmbientLight(0xdbeafe, 1.2);
    scene.add(skyLight);

    // Bounce Light
    const groundBounce = new THREE.DirectionalLight(0x94a3b8, 1.0);
    groundBounce.position.set(-10, -10, -5);
    scene.add(groundBounce);

    // Volumetric High-Altitude Clouds Layer
    const cloudsGroup = new THREE.Group();
    cloudsGroup.position.y = -7.0;
    cloudsGroupRef.current = cloudsGroup;

    const cloudMat = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9,
      transparent: true,
      opacity: 0.65,
      roughness: 0.9,
    });

    for (let c = 0; c < 24; c++) {
      const cloudPuff = new THREE.Mesh(
        new THREE.SphereGeometry(3.5 + Math.random() * 2.5, 16, 16),
        cloudMat
      );
      cloudPuff.scale.set(2.5, 0.4, 1.8);
      cloudPuff.position.set(
        (Math.random() - 0.5) * 60,
        (Math.random() - 0.5) * 1.5,
        (Math.random() - 0.5) * 60
      );
      cloudsGroup.add(cloudPuff);
    }
    scene.add(cloudsGroup);

    // Build Hyper-Realistic 3D MALE UAV Aircraft Model
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

    // Resize Handler
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // Animation Loop
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      if (controlsRef.current) {
        controlsRef.current.autoRotate = autoRotate && !selectedComponent;
        controlsRef.current.autoRotateSpeed = 0.8;
        controlsRef.current.update();
      }

      // Drift Clouds
      if (cloudsGroupRef.current) {
        cloudsGroupRef.current.position.z += delta * 1.5;
        if (cloudsGroupRef.current.position.z > 20) {
          cloudsGroupRef.current.position.z = -20;
        }
      }

      // Aerodynamic pitch oscillation
      if (modelRef.current) {
        engineModel.engineRootGroup.rotation.z = Math.sin(elapsedTime * 0.5) * 0.015;
        engineModel.engineRootGroup.position.y = Math.sin(elapsedTime * 0.8) * 0.08;
      }

      // --- Telemetry Kinematics ---
      const activeFrame = useDigitalTwinStore.getState().currentFrame;
      const activeRpm = activeFrame?.telemetry?.rpm ?? rpm;
      const rps = activeRpm / 60;
      crankAngleRef.current += rps * delta * Math.PI * 2;
      const theta = crankAngleRef.current;

      if (modelRef.current) {
        const { kinematics } = modelRef.current;

        // Rotate Crankshaft & Rear Pusher Propeller
        kinematics.crankGroup.rotation.z = theta;
        kinematics.propellerGroup.rotation.z = -theta;

        // EO/IR Chin Turret Scanning Movement
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
            kinematics.sparkLights[piston.cylinderIndex].intensity = isNearTDC ? 4.0 : 0.0;
          }
        });
      }

      // Screen-Space Hotspot Projections with Avionics Leader Lines
      if (showHotspots && cameraRef.current && modelRef.current && containerRef.current) {
        const projectedHotspots: HotspotProjection[] = [];
        const w = containerRef.current.clientWidth;
        const h = containerRef.current.clientHeight;

        modelRef.current.components.forEach((comp) => {
          if (!comp.sensorKey) return;

          // Component origin in 3D
          const compWorldOrigin = comp.group.position.clone();
          compWorldOrigin.project(cameraRef.current!);

          // Spatially offset callout point in 3D
          const compWorldOffset = comp.group.position.clone().add(comp.hotspotOffset);
          compWorldOffset.project(cameraRef.current!);

          if (compWorldOrigin.z < 1.0 && compWorldOffset.z < 1.0) {
            const originX = (compWorldOrigin.x * 0.5 + 0.5) * w;
            const originY = (-(compWorldOrigin.y * 0.5) + 0.5) * h;

            const badgeX = (compWorldOffset.x * 0.5 + 0.5) * w;
            const badgeY = (-(compWorldOffset.y * 0.5) + 0.5) * h;

            let valStr = '';
            let isAlert = false;

            if (comp.sensorKey === 'rpm') valStr = `${Math.round(activeRpm)} RPM`;
            else if (comp.sensorKey === 'cht1') {
              valStr = `${Math.round(cht1)}°C`;
              isAlert = cht1 > 175;
            } else if (comp.sensorKey === 'cht2') {
              valStr = `${Math.round(cht2)}°C`;
              isAlert = cht2 > 175;
            } else if (comp.sensorKey === 'cht3') {
              valStr = `${Math.round(cht3)}°C`;
              isAlert = cht3 > 175;
            } else if (comp.sensorKey === 'cht4') {
              valStr = `${Math.round(cht4)}°C`;
              isAlert = cht4 > 175;
            } else if (comp.sensorKey === 'oil_pressure') {
              valStr = `${oilPressure.toFixed(1)} bar`;
              isAlert = oilPressure < 2.0;
            } else if (comp.sensorKey === 'map') {
              valStr = `${map.toFixed(1)} inHg`;
            } else if (comp.sensorKey === 'egt1') {
              valStr = `${Math.round(egt1)}°C`;
              isAlert = egt1 > 880;
            }

            // Filtering logic to keep screen 100% clean
            let include = true;
            if (hotspotFilter === 'ALERTS_ONLY' && !isAlert) include = false;
            else if (hotspotFilter === 'CRITICAL' && !['rpm', 'cht1', 'oil_pressure', 'map'].includes(comp.sensorKey)) include = false;

            if (include) {
              projectedHotspots.push({
                id: comp.id,
                name: comp.name,
                val: valStr,
                originX,
                originY,
                badgeX,
                badgeY,
                alert: isAlert,
                isHovered: comp.id === hoveredHotspotId,
              });
            }
          }
        });

        setHotspotPositions(projectedHotspots);
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('pointerdown', handleCanvasClick);
      renderer.dispose();
    };
  }, [hotspotFilter, hoveredHotspotId]);

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
            if (comp.id === 'male_uav_airframe') {
              mesh.material = materials.glassXray;
            } else if (comp.id.startsWith('cylinder')) {
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
            // REALISTIC Mode matching reference photo!
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
    <div
      className={`relative bg-slate-950/90 border border-slate-800 rounded-xl overflow-hidden shadow-2xl transition-all duration-300 ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none border-none' : 'w-full h-[700px]'
      }`}
    >
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* SVG AVIONICS LEADER LINES OVERLAY (CONNECTS 3D ANCHORS TO HUD BADGES) */}
      {showHotspots && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-10 overflow-visible">
          <defs>
            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.4" />
            </linearGradient>
            <linearGradient id="lineAlertGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.5" />
            </linearGradient>
          </defs>

          {hotspotPositions.map((hs) => {
            // Midpoint elbow joint for clean 45-degree avionics callout line
            const midX = (hs.originX + hs.badgeX) / 2;
            const midY = hs.badgeY;
            const isAlert = hs.alert;
            const isHover = hs.isHovered;

            return (
              <g key={`svg-line-${hs.id}`}>
                {/* Reticle Target Circle at 3D Component Origin */}
                <circle
                  cx={hs.originX}
                  cy={hs.originY}
                  r={isHover ? 6 : 4}
                  fill={isAlert ? '#ef4444' : '#38bdf8'}
                  className="animate-pulse"
                />
                <circle
                  cx={hs.originX}
                  cy={hs.originY}
                  r={isHover ? 12 : 8}
                  fill="none"
                  stroke={isAlert ? '#ef4444' : '#38bdf8'}
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />

                {/* Leader Line Path with Elbow Joint */}
                <polyline
                  points={`${hs.originX},${hs.originY} ${midX},${midY} ${hs.badgeX},${hs.badgeY}`}
                  fill="none"
                  stroke={isAlert ? 'url(#lineAlertGrad)' : 'url(#lineGrad)'}
                  strokeWidth={isHover ? '2.5' : '1.5'}
                  strokeDasharray={isHover ? 'none' : '4 2'}
                />
              </g>
            );
          })}
        </svg>
      )}

      {/* Top Header Avionics HUD */}
      <div className="absolute top-4 left-4 right-4 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-3 bg-slate-900/90 backdrop-blur-md px-4 py-2.5 rounded-lg border border-slate-700/70 shadow-2xl pointer-events-auto">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-ping" />
          <div>
            <div className="flex items-center gap-2">
              <Plane className="w-4 h-4 text-cyan-400" />
              <h3 className="font-mono text-xs font-bold text-cyan-400 tracking-wider uppercase">
                REAL MALE UAV AIRBORNE DRONE DIGITAL TWIN (N190TC)
              </h3>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono border border-emerald-500/30 font-bold">
                AIRBORNE 18,500 FT
              </span>
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

      {/* Floating Spatially Separated 3D Hotspot Sensor Badges */}
      {showHotspots &&
        hotspotPositions.map((hs) => (
          <div
            key={hs.id}
            style={{ left: `${hs.badgeX}px`, top: `${hs.badgeY}px` }}
            onMouseEnter={() => setHoveredHotspotId(hs.id)}
            onMouseLeave={() => setHoveredHotspotId(null)}
            className={`absolute -translate-x-1/2 -translate-y-1/2 pointer-events-auto transition-all duration-150 ${
              hs.isHovered ? 'z-30 scale-105' : hs.alert ? 'z-20' : 'z-10'
            }`}
          >
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md backdrop-blur-lg border shadow-xl text-[11px] font-mono whitespace-nowrap cursor-pointer transition-all ${
                hs.alert
                  ? 'bg-rose-950/90 border-rose-500 text-rose-200 animate-pulse shadow-rose-900/50'
                  : hs.isHovered
                  ? 'bg-cyan-950/90 border-cyan-400 text-cyan-100 shadow-cyan-500/30'
                  : 'bg-slate-900/85 border-slate-700/80 text-slate-200 hover:border-cyan-500/50'
              }`}
            >
              <div className={`w-2.5 h-2.5 rounded-full ${hs.alert ? 'bg-rose-400 animate-ping' : 'bg-cyan-400'}`} />
              <span className="text-slate-400">{hs.name}:</span>
              <span className="font-bold text-cyan-300">{hs.val}</span>
            </div>
          </div>
        ))}

      {/* Bottom Control Bar with Hotspot Filter Options */}
      <div className="absolute bottom-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Camera Angles Presets matching photo */}
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

          {/* Filter Dropdown */}
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
  );
};

export default AeroPistonEngine3D;
