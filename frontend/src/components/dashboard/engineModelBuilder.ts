import * as THREE from 'three';

export interface EngineComponentRef {
  id: string;
  name: string;
  group: THREE.Group;
  defaultPosition: THREE.Vector3;
  explodedDirection: THREE.Vector3;
  meshMaterials: (THREE.MeshStandardMaterial | THREE.MeshPhysicalMaterial)[];
  originalColors: THREE.Color[];
  hotspotOffset: THREE.Vector3;
  sensorKey?: string;
}

export interface EngineKinematics {
  crankGroup: THREE.Group;
  propellerGroup: THREE.Group;
  pistons: {
    group: THREE.Group;
    rodGroup: THREE.Group;
    cylinderIndex: number;
    baseX: number;
    sideSign: number;
    phaseAngle: number;
  }[];
  sparkLights: THREE.PointLight[];
  exhaustPipes: THREE.Mesh[];
  cylinderBarrels: THREE.Mesh[];
  sensorTurret?: THREE.Group;
}

export interface BuiltEngineModel {
  engineRootGroup: THREE.Group;
  components: Map<string, EngineComponentRef>;
  kinematics: EngineKinematics;
  materials: {
    uavMainPhysicalSkin: THREE.MeshPhysicalMaterial;
    uavPanelDarkSkin: THREE.MeshPhysicalMaterial;
    uavRadomeMat: THREE.MeshPhysicalMaterial;
    castAluminum: THREE.MeshStandardMaterial;
    rotaxGreenValve: THREE.MeshStandardMaterial;
    castIronCylinder: THREE.MeshStandardMaterial;
    darkSteel: THREE.MeshStandardMaterial;
    chrome: THREE.MeshStandardMaterial;
    carbonProp: THREE.MeshStandardMaterial;
    goldAccent: THREE.MeshStandardMaterial;
    copperPipe: THREE.MeshStandardMaterial;
    exhaustHot: THREE.MeshStandardMaterial;
    yellowIgnitionWire: THREE.MeshStandardMaterial;
    glassXray: THREE.MeshPhysicalMaterial;
    wireframe: THREE.MeshBasicMaterial;
  };
}

// Procedural Military Aircraft Panel & Stencil Texture Map (N190TC Callsign + EXPERIMENTAL)
function createMilitaryDecalTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 2048;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d')!;

  // Base military slate gray (#7c8d9e)
  ctx.fillStyle = '#7c8d9e';
  ctx.fillRect(0, 0, 2048, 1024);

  // Structural Panel Seams
  ctx.strokeStyle = '#5a6b7e';
  ctx.lineWidth = 3;

  for (let x = 128; x < 2048; x += 256) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, 1024);
    ctx.stroke();
  }
  for (let y = 128; y < 1024; y += 256) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(2048, y);
    ctx.stroke();
  }

  // Access Hatches & Rivets
  ctx.strokeStyle = '#4a5b6e';
  ctx.lineWidth = 2;
  ctx.strokeRect(300, 200, 180, 120);
  ctx.strokeRect(600, 450, 220, 140);
  ctx.strokeRect(1200, 300, 160, 200);

  // Callsign Stencil "N190TC"
  ctx.font = 'bold 110px "Courier New", monospace';
  ctx.fillStyle = '#1e293b';
  ctx.fillText('N190TC', 1350, 480);

  // Secondary Text "DRDO PS-26054"
  ctx.font = 'bold 50px "Courier New", monospace';
  ctx.fillStyle = '#334155';
  ctx.fillText('DRDO PS-26054', 1350, 560);

  // Red EXPERIMENTAL Warning Box
  ctx.strokeStyle = '#dc2626';
  ctx.lineWidth = 6;
  ctx.strokeRect(240, 400, 420, 110);
  ctx.font = 'bold 52px sans-serif';
  ctx.fillStyle = '#dc2626';
  ctx.fillText('EXPERIMENTAL', 265, 475);

  // DANGER PROPELLER & NO STEP Warnings
  ctx.font = 'bold 28px sans-serif';
  ctx.fillStyle = '#dc2626';
  ctx.fillText('DANGER PROPELLER', 1550, 850);
  ctx.fillText('NO STEP', 850, 250);
  ctx.fillText('NO STEP', 850, 750);

  const texture = new THREE.CanvasTexture(canvas);
  return texture;
}

/**
 * Builds a 1:1 CAD-grade photorealistic MALE UAV Aircraft (MQ-9 SkyGuardian / TAPAS MALE UAV)
 * with spatially separated 3D hotspot callout vectors to eliminate visual congestion.
 */
export function createAeroPistonEngineModel(): BuiltEngineModel {
  const engineRootGroup = new THREE.Group();
  engineRootGroup.name = 'MALE_UAV_Photorealistic_Aircraft';

  const components = new Map<string, EngineComponentRef>();
  const decalTexture = createMilitaryDecalTexture();

  // --- Photorealistic Aircraft Physical Materials ---
  const uavMainPhysicalSkin = new THREE.MeshPhysicalMaterial({
    color: 0x8aa0b5,
    map: decalTexture,
    metalness: 0.2,
    roughness: 0.32,
    clearcoat: 0.45,
    clearcoatRoughness: 0.12,
    name: 'MilitaryCompositeSkin',
  });

  const uavPanelDarkSkin = new THREE.MeshPhysicalMaterial({
    color: 0x334155,
    metalness: 0.4,
    roughness: 0.35,
    clearcoat: 0.3,
    name: 'DarkAvionicsPanel',
  });

  const uavRadomeMat = new THREE.MeshPhysicalMaterial({
    color: 0x94a3b8,
    metalness: 0.1,
    roughness: 0.25,
    clearcoat: 0.5,
    name: 'NoseRadomeSkin',
  });

  const castAluminum = new THREE.MeshStandardMaterial({
    color: 0xcbd5e1,
    metalness: 0.85,
    roughness: 0.35,
    name: 'CastAluminumCrankcase',
  });

  const rotaxGreenValve = new THREE.MeshStandardMaterial({
    color: 0x15803d,
    metalness: 0.3,
    roughness: 0.3,
    name: 'RotaxGreenValveCover',
  });

  const castIronCylinder = new THREE.MeshStandardMaterial({
    color: 0x3f3f46,
    metalness: 0.75,
    roughness: 0.45,
    name: 'CastIronCylinderBarrel',
  });

  const darkSteel = new THREE.MeshStandardMaterial({
    color: 0x0f172a,
    metalness: 0.9,
    roughness: 0.25,
    name: 'StructuralSteel',
  });

  const chrome = new THREE.MeshStandardMaterial({
    color: 0xf8fafc,
    metalness: 0.98,
    roughness: 0.08,
    name: 'PolishedChrome',
  });

  const carbonProp = new THREE.MeshStandardMaterial({
    color: 0x0f172a,
    metalness: 0.6,
    roughness: 0.25,
    name: 'CarbonCompositeProp',
  });

  const goldAccent = new THREE.MeshStandardMaterial({
    color: 0xd97706,
    metalness: 0.85,
    roughness: 0.25,
    name: 'AnodizedGoldSump',
  });

  const copperPipe = new THREE.MeshStandardMaterial({
    color: 0xb45309,
    metalness: 0.8,
    roughness: 0.3,
    name: 'CopperAlloy',
  });

  const exhaustHot = new THREE.MeshStandardMaterial({
    color: 0x78350f,
    metalness: 0.8,
    roughness: 0.4,
    emissive: 0x451a03,
    emissiveIntensity: 0.2,
    name: 'ExhaustHeader',
  });

  const yellowIgnitionWire = new THREE.MeshStandardMaterial({
    color: 0xeab308,
    metalness: 0.1,
    roughness: 0.4,
    name: 'IgnitionHarnessYellow',
  });

  const glassXray = new THREE.MeshPhysicalMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.22,
    roughness: 0.1,
    metalness: 0.1,
    transmission: 0.85,
    ior: 1.5,
    name: 'XRayTranslucent',
  });

  const wireframe = new THREE.MeshBasicMaterial({
    color: 0x06b6d4,
    wireframe: true,
    name: 'AvionicsWireframe',
  });

  const materials = {
    uavMainPhysicalSkin,
    uavPanelDarkSkin,
    uavRadomeMat,
    castAluminum,
    rotaxGreenValve,
    castIronCylinder,
    darkSteel,
    chrome,
    carbonProp,
    goldAccent,
    copperPipe,
    exhaustHot,
    yellowIgnitionWire,
    glassXray,
    wireframe,
  };

  const sparkLights: THREE.PointLight[] = [];
  const exhaustPipes: THREE.Mesh[] = [];
  const cylinderBarrels: THREE.Mesh[] = [];
  const pistonsKinematics: EngineKinematics['pistons'] = [];

  const registerComponent = (
    id: string,
    name: string,
    group: THREE.Group,
    explodedDirection: THREE.Vector3,
    hotspotOffset: THREE.Vector3 = new THREE.Vector3(0, 0, 0),
    sensorKey?: string
  ): EngineComponentRef => {
    group.name = id;
    const meshMaterials: (THREE.MeshStandardMaterial | THREE.MeshPhysicalMaterial)[] = [];
    const originalColors: THREE.Color[] = [];

    group.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach((m) => {
            if (m instanceof THREE.MeshStandardMaterial || m instanceof THREE.MeshPhysicalMaterial) {
              meshMaterials.push(m);
              originalColors.push(m.color.clone());
            }
          });
        } else if (mesh.material instanceof THREE.MeshStandardMaterial || mesh.material instanceof THREE.MeshPhysicalMaterial) {
          meshMaterials.push(mesh.material);
          originalColors.push(mesh.material.color.clone());
        }
      }
    });

    const ref: EngineComponentRef = {
      id,
      name,
      group,
      defaultPosition: group.position.clone(),
      explodedDirection,
      meshMaterials,
      originalColors,
      hotspotOffset,
      sensorKey,
    };

    components.set(id, ref);
    engineRootGroup.add(group);
    return ref;
  };

  // ==========================================
  // 1. AERODYNAMIC AIRFRAME
  // ==========================================
  const uavFuselageGroup = new THREE.Group();

  const fuselageCrossShape = new THREE.Shape();
  fuselageCrossShape.moveTo(0, 0.65);
  fuselageCrossShape.bezierCurveTo(0.55, 0.65, 0.65, 0.15, 0.55, -0.4);
  fuselageCrossShape.bezierCurveTo(0.35, -0.7, -0.35, -0.7, -0.55, -0.4);
  fuselageCrossShape.bezierCurveTo(-0.65, 0.15, -0.55, 0.65, 0, 0.65);

  const fuselagePath = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0, 5.8),
    new THREE.Vector3(0, 0.3, 4.4),
    new THREE.Vector3(0, 0.45, 2.6),
    new THREE.Vector3(0, 0.25, 0.0),
    new THREE.Vector3(0, 0.15, -2.4),
    new THREE.Vector3(0, 0.05, -4.0),
  ]);

  const fuselageGeo = new THREE.ExtrudeGeometry(fuselageCrossShape, {
    extrudePath: fuselagePath,
    steps: 64,
    bevelEnabled: false,
  });
  const fuselageMesh = new THREE.Mesh(fuselageGeo, uavMainPhysicalSkin);
  fuselageMesh.castShadow = true;
  fuselageMesh.receiveShadow = true;
  uavFuselageGroup.add(fuselageMesh);

  // Radome & Pitot
  const radomeGeo = new THREE.SphereGeometry(0.72, 32, 24);
  radomeGeo.scale(0.85, 0.9, 1.6);
  const radomeMesh = new THREE.Mesh(radomeGeo, uavRadomeMat);
  radomeMesh.position.set(0, 0.12, 4.8);
  uavFuselageGroup.add(radomeMesh);

  const pitotMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.035, 0.85, 12), chrome);
  pitotMesh.rotation.x = Math.PI / 2;
  pitotMesh.position.set(0, 0.12, 6.2);
  uavFuselageGroup.add(pitotMesh);

  // SATCOM Dome
  const satcomGeo = new THREE.SphereGeometry(0.75, 32, 16);
  satcomGeo.scale(0.68, 0.48, 1.85);
  const satcomMesh = new THREE.Mesh(satcomGeo, uavMainPhysicalSkin);
  satcomMesh.position.set(0, 0.72, 3.2);
  uavFuselageGroup.add(satcomMesh);

  // EO/IR Chin Turret
  const sensorTurretGroup = new THREE.Group();
  sensorTurretGroup.position.set(0, -0.68, 4.6);

  const turretHousing = new THREE.Mesh(new THREE.SphereGeometry(0.42, 24, 24), uavPanelDarkSkin);
  sensorTurretGroup.add(turretHousing);

  const primaryLens = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.1, 16), chrome);
  primaryLens.rotation.x = Math.PI / 2;
  primaryLens.position.set(0, -0.05, 0.36);
  sensorTurretGroup.add(primaryLens);

  uavFuselageGroup.add(sensorTurretGroup);

  // Wings
  const airfoilShape = new THREE.Shape();
  airfoilShape.moveTo(0.65, 0);
  airfoilShape.bezierCurveTo(0.45, 0.09, -0.2, 0.07, -0.65, 0.01);
  airfoilShape.bezierCurveTo(-0.65, -0.01, -0.2, -0.04, 0.65, 0);

  const wingExtrudeSettings = { depth: 8.2, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02 };

  const rightWingMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(airfoilShape, wingExtrudeSettings), uavMainPhysicalSkin);
  rightWingMesh.rotation.y = Math.PI / 2;
  rightWingMesh.rotation.x = 0.035;
  rightWingMesh.position.set(0.65, 0.15, 0.6);
  uavFuselageGroup.add(rightWingMesh);

  const wingletShape = new THREE.Shape();
  wingletShape.moveTo(0, 0);
  wingletShape.lineTo(0.35, 1.35);
  wingletShape.lineTo(-0.12, 1.45);
  wingletShape.lineTo(-0.35, 0);
  wingletShape.closePath();

  const rightWinglet = new THREE.Mesh(new THREE.ExtrudeGeometry(wingletShape, { depth: 0.08 }), uavPanelDarkSkin);
  rightWinglet.rotation.y = -0.18;
  rightWinglet.position.set(8.75, 0.35, 0.6);
  uavFuselageGroup.add(rightWinglet);

  const leftWingMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(airfoilShape, wingExtrudeSettings), uavMainPhysicalSkin);
  leftWingMesh.rotation.y = -Math.PI / 2;
  leftWingMesh.rotation.x = -0.035;
  leftWingMesh.position.set(-0.65, 0.15, 0.6);
  uavFuselageGroup.add(leftWingMesh);

  const leftWinglet = new THREE.Mesh(new THREE.ExtrudeGeometry(wingletShape, { depth: 0.08 }), uavPanelDarkSkin);
  leftWinglet.rotation.y = 0.18;
  leftWinglet.position.set(-8.75, 0.35, 0.6);
  uavFuselageGroup.add(leftWinglet);

  // V-Tail Fins
  const vTailAirfoil = new THREE.Shape();
  vTailAirfoil.moveTo(0, 0);
  vTailAirfoil.lineTo(0.55, 2.4);
  vTailAirfoil.lineTo(0.12, 2.5);
  vTailAirfoil.lineTo(-0.45, 0);
  vTailAirfoil.closePath();
  const vTailGeo = new THREE.ExtrudeGeometry(vTailAirfoil, { depth: 0.1, bevelEnabled: true });

  const rightVTail = new THREE.Mesh(vTailGeo, uavMainPhysicalSkin);
  rightVTail.rotation.z = -Math.PI / 3.6;
  rightVTail.rotation.y = -0.18;
  rightVTail.position.set(0.45, 0.25, -3.3);
  uavFuselageGroup.add(rightVTail);

  const leftVTail = new THREE.Mesh(vTailGeo, uavMainPhysicalSkin);
  leftVTail.rotation.z = Math.PI / 3.6;
  leftVTail.rotation.y = 0.18;
  leftVTail.position.set(-0.45, 0.25, -3.3);
  uavFuselageGroup.add(leftVTail);

  // Dorsal Scoop
  const scoopGeo = new THREE.CylinderGeometry(0.38, 0.48, 0.95, 24, 1, true);
  const scoopMesh = new THREE.Mesh(scoopGeo, uavPanelDarkSkin);
  scoopMesh.rotation.x = Math.PI / 2;
  scoopMesh.position.set(0, 0.82, -0.8);
  uavFuselageGroup.add(scoopMesh);

  // Engine Nacelle Casing
  const engineNacelleGeo = new THREE.CylinderGeometry(0.88, 0.78, 2.6, 24, 1, true);
  const engineNacelleMesh = new THREE.Mesh(engineNacelleGeo, glassXray);
  engineNacelleMesh.rotation.x = Math.PI / 2;
  engineNacelleMesh.position.set(0, 0.1, -1.2);
  uavFuselageGroup.add(engineNacelleMesh);

  registerComponent(
    'male_uav_airframe',
    'MALE UAV Airframe (N190TC)',
    uavFuselageGroup,
    new THREE.Vector3(0, 2.2, 0),
    new THREE.Vector3(0, 1.6, 2.0)
  );

  // ==========================================
  // 2. ROTAX 914 AERO ENGINE WITH SPATIALLY SEPARATED CALLOUT VECTORS
  // ==========================================

  // Crankcase Sump - Offset Downward Callout Vector
  const crankcaseGroup = new THREE.Group();
  crankcaseGroup.position.set(0, 0.1, -1.2);

  const blockMesh = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.2, 2.6), castAluminum);
  crankcaseGroup.add(blockMesh);

  const sumpShape = new THREE.Shape();
  sumpShape.moveTo(-0.6, 0);
  sumpShape.lineTo(0.6, 0);
  sumpShape.lineTo(0.4, -0.5);
  sumpShape.lineTo(-0.4, -0.5);
  sumpShape.closePath();
  const sumpMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(sumpShape, { depth: 2.2 }), goldAccent);
  sumpMesh.position.set(0, -0.85, -1.1);
  crankcaseGroup.add(sumpMesh);

  registerComponent(
    'crankcase',
    'Oil System & Crankcase',
    crankcaseGroup,
    new THREE.Vector3(0, -0.8, 0),
    new THREE.Vector3(0, -1.8, -0.8), // Spatially offset downward callout
    'oil_pressure'
  );

  // Crankshaft
  const crankGroup = new THREE.Group();
  crankGroup.position.set(0, 0.1, -1.2);
  const mainShaftMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 3.4, 32), chrome);
  mainShaftMesh.rotation.x = Math.PI / 2;
  crankGroup.add(mainShaftMesh);

  const crankPhases = [0, Math.PI, 0, Math.PI];
  [0.6, 0.1, -0.4, -0.9].forEach((zPos, idx) => {
    const cwGroup = new THREE.Group();
    cwGroup.position.set(0, 0, zPos);
    cwGroup.rotation.z = crankPhases[idx];
    cwGroup.add(new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.18, 16), chrome));
    crankGroup.add(cwGroup);
  });
  engineRootGroup.add(crankGroup);

  // Rear Pusper Propeller - Offset Upward Aft Callout Vector
  const propellerGroup = new THREE.Group();
  propellerGroup.position.set(0, 0.08, -4.12);

  const spinnerMesh = new THREE.Mesh(new THREE.ConeGeometry(0.44, 0.95, 32), chrome);
  spinnerMesh.rotation.x = -Math.PI / 2;
  spinnerMesh.position.set(0, 0, -0.48);
  propellerGroup.add(spinnerMesh);

  for (let b = 0; b < 3; b++) {
    const bladeAngle = (b * Math.PI * 2) / 3;
    const bladeHolder = new THREE.Group();
    bladeHolder.rotation.z = bladeAngle;
    const bladeMesh = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.2, 0.04), carbonProp);
    bladeMesh.position.set(0, 1.1, 0);
    bladeHolder.add(bladeMesh);
    propellerGroup.add(bladeHolder);
  }

  registerComponent(
    'propeller',
    '3-Blade Pusher Propeller',
    propellerGroup,
    new THREE.Vector3(0, 0, -1.8),
    new THREE.Vector3(0, 2.2, -4.2), // Spatially offset upward aft callout
    'rpm'
  );

  // 4 Cylinders - Spatially Offset Left & Right Outer Callout Vectors!
  const cylinderConfigs = [
    { side: 1, z: -0.6, idx: 0, id: 'cylinder_1', name: 'Cylinder #1 (Right Front)', key: 'cht1', offset: new THREE.Vector3(3.2, 1.6, -0.2) },
    { side: 1, z: -1.6, idx: 1, id: 'cylinder_2', name: 'Cylinder #2 (Right Rear)', key: 'cht2', offset: new THREE.Vector3(3.6, -1.2, -2.0) },
    { side: -1, z: -1.0, idx: 2, id: 'cylinder_3', name: 'Cylinder #3 (Left Front)', key: 'cht3', offset: new THREE.Vector3(-3.2, 1.6, -0.6) },
    { side: -1, z: -2.0, idx: 3, id: 'cylinder_4', name: 'Cylinder #4 (Left Rear)', key: 'cht4', offset: new THREE.Vector3(-3.6, -1.2, -2.4) },
  ];

  cylinderConfigs.forEach((cfg) => {
    const cylGroup = new THREE.Group();
    const sideSign = cfg.side;
    cylGroup.position.set(sideSign * 1.3, 0.1, cfg.z);
    const expDir = new THREE.Vector3(sideSign * 1.2, 0.2, 0);

    const barrelMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.48, 1.0, 24), castIronCylinder);
    barrelMesh.rotation.z = Math.PI / 2;
    cylGroup.add(barrelMesh);
    cylinderBarrels.push(barrelMesh);

    const headMesh = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.95, 0.95), rotaxGreenValve);
    headMesh.position.set(sideSign * 0.6, 0, 0);
    cylGroup.add(headMesh);

    const sparkLight = new THREE.PointLight(0x38bdf8, 0, 2.5);
    sparkLight.position.set(sideSign * 0.5, 0.1, 0);
    cylGroup.add(sparkLight);
    sparkLights.push(sparkLight);

    registerComponent(
      cfg.id,
      cfg.name,
      cylGroup,
      expDir,
      cfg.offset, // Clean, non-overlapping spatial callout vector!
      cfg.key
    );

    const pistonGroup = new THREE.Group();
    const pistonMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.4, 24), chrome);
    pistonMesh.rotation.z = Math.PI / 2;
    pistonGroup.add(pistonMesh);

    const rodGroup = new THREE.Group();
    const rodMesh = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.1, 0.12), darkSteel);
    rodMesh.position.set(-sideSign * 0.45, 0, 0);
    rodGroup.add(rodMesh);

    pistonGroup.add(rodGroup);
    engineRootGroup.add(pistonGroup);

    pistonsKinematics.push({
      group: pistonGroup,
      rodGroup,
      cylinderIndex: cfg.idx,
      baseX: sideSign * 0.7,
      sideSign,
      phaseAngle: (cfg.idx === 0 || cfg.idx === 2) ? 0 : Math.PI,
    });
  });

  // Turbocharger - Offset Top Center Callout Vector
  const turboGroup = new THREE.Group();
  turboGroup.position.set(0, 0.9, -2.1);
  turboGroup.add(new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.18, 16, 32), castAluminum));

  registerComponent(
    'turbocharger',
    'Rotax Turbocharger',
    turboGroup,
    new THREE.Vector3(0, 1.0, -0.4),
    new THREE.Vector3(0, 2.6, -2.1), // Top center callout vector
    'map'
  );

  // Exhaust - Offset Rear Bottom Callout Vector
  const exhaustGroup = new THREE.Group();
  cylinderConfigs.forEach((cfg) => {
    const sideSign = cfg.side;
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(sideSign * 1.2, -0.2, cfg.z),
      new THREE.Vector3(sideSign * 0.7, -0.7, cfg.z * 0.8),
      new THREE.Vector3(0, -0.9, -2.4),
    ]);
    const exhMesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 20, 0.1, 16, false), exhaustHot);
    exhaustGroup.add(exhMesh);
    exhaustPipes.push(exhMesh);
  });

  registerComponent(
    'exhaust_manifold',
    'Exhaust Header & Collector',
    exhaustGroup,
    new THREE.Vector3(0, -1.0, -0.4),
    new THREE.Vector3(0, -2.4, -3.2), // Rear bottom callout vector
    'egt1'
  );

  return {
    engineRootGroup,
    components,
    kinematics: {
      crankGroup,
      propellerGroup,
      pistons: pistonsKinematics,
      sparkLights,
      exhaustPipes,
      cylinderBarrels,
      sensorTurret: sensorTurretGroup,
    },
    materials,
  };
}
