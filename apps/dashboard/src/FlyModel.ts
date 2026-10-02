import * as THREE from "three";

function tube(points: THREE.Vector3[], radius: number, material: THREE.Material) {
  return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 12, radius, 5, false), material);
}

/** An illustrated specimen: authored geometry, not a scanned biological mesh. */
export function createFly() {
  const fly = new THREE.Group();
  const shell = new THREE.MeshStandardMaterial({ color: 0x66503c, roughness: .54, metalness: .18 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x28241f, roughness: .58 });
  const gold = new THREE.MeshStandardMaterial({ color: 0xae8850, roughness: .58, metalness: .1 });
  const vein = new THREE.MeshStandardMaterial({ color: 0x9cafab, transparent: true, opacity: .48, roughness: .6 });
  const ellipsoid = (radius: number, material: THREE.Material, position: [number, number, number], scale: [number, number, number]) => {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 28, 20), material);
    mesh.position.set(...position); mesh.scale.set(...scale); mesh.castShadow = true; fly.add(mesh); return mesh;
  };
  ellipsoid(.27, shell, [0, 0, 0], [1.15, 1, .85]);
  // Tapered overlapping abdominal segments with dark transverse bands.
  for (let i = 0; i < 6; i++) {
    const radius = .23 * Math.sin((i + 2) / 8 * Math.PI);
    ellipsoid(radius, i % 2 ? dark : gold, [-.27 - i * .1, -.055 - i * .012, 0], [.65, .85, 1]);
  }
  ellipsoid(.215, dark, [.35, .025, 0], [.85, 1, 1.18]);
  const eyeMaterial = new THREE.MeshStandardMaterial({ color: 0xad3045, roughness: .36, metalness: .2 });
  const facetMaterial = new THREE.MeshStandardMaterial({ color: 0xd44d58, roughness: .5, metalness: .17 });
  for (const side of [-1, 1]) {
    const center = new THREE.Vector3(.39, .055, side * .155);
    ellipsoid(.155, eyeMaterial, [center.x, center.y, center.z], [.8, 1.1, .8]);
    const facets = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.019, 0), facetMaterial, 65);
    const dummy = new THREE.Object3D();
    for (let i = 0; i < 65; i++) {
      const angle = i * 2.39996, z = 1 - (i + .5) / 65;
      const r = Math.sqrt(1 - z * z);
      dummy.position.set(center.x + Math.cos(angle) * r * .125, center.y + Math.sin(angle) * r * .17, center.z + side * z * .126);
      dummy.updateMatrix(); facets.setMatrixAt(i, dummy.matrix);
    }
    fly.add(facets);
    // Antennae and fine arista-like branches.
    fly.add(tube([new THREE.Vector3(.49, .14, side * .07), new THREE.Vector3(.59, .24, side * .11), new THREE.Vector3(.67, .31, side * .18)], .009, dark));
    for (let i = 0; i < 4; i++) fly.add(tube([new THREE.Vector3(.57 + i * .025, .22 + i * .025, side * (.1 + i * .02)), new THREE.Vector3(.57 + i * .025, .3 + i * .025, side * (.17 + i * .02))], .003, dark));
    // Three articulated legs on each side of the thorax.
    for (let i = 0; i < 3; i++) {
      const leg = new THREE.Group(); leg.name = "leg"; leg.userData = { side, ordinal: i };
      const baseX = .14 - i * .17, extension = .38 - i * .35;
      leg.add(tube([new THREE.Vector3(baseX, -.1, side * .13), new THREE.Vector3(extension, -.26, side * .35), new THREE.Vector3(extension + .1, -.57, side * .5), new THREE.Vector3(extension + .22, -.6, side * .59)], .017, dark));
      fly.add(leg);
    }
    const wingGroup = new THREE.Group(); wingGroup.name = "wing"; wingGroup.userData.side = side;
    wingGroup.position.set(-.04, .21, side * .11);
    const shape = new THREE.Shape(); shape.moveTo(0, 0); shape.bezierCurveTo(-.3, .13, -.83, .28, -1.02, .6); shape.bezierCurveTo(-1.22, .94, -.76, 1.01, -.45, .7); shape.bezierCurveTo(-.15, .43, .07, .18, 0, 0);
    const wing = new THREE.Mesh(new THREE.ShapeGeometry(shape, 24), new THREE.MeshPhysicalMaterial({ color: 0xd1e3e7, transparent: true, opacity: .32, side: THREE.DoubleSide, metalness: .22, roughness: .2, depthWrite: false }));
    wing.rotation.x = side * Math.PI / 2; wingGroup.add(wing);
    for (let i = 0; i < 4; i++) {
      const points = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(-.26 - i * .08, .008, side * (.22 + i * .06)), new THREE.Vector3(-.49 - i * .16, .006, side * (.71 - i * .045))];
      wingGroup.add(tube(points, .004, vein));
    }
    fly.add(wingGroup);
    // Small haltere behind each wing base.
    fly.add(tube([new THREE.Vector3(-.17, .02, side * .19), new THREE.Vector3(-.26, .1, side * .34)], .009, gold));
    ellipsoid(.027, gold, [-.26, .1, side * .34], [1, 1, 1]);
  }
  // Dorsal bristles provide a visible silhouette at specimen zoom.
  for (let i = 0; i < 24; i++) {
    const angle = i * 2.39996, x = -.19 + (i % 6) * .065, z = Math.sin(angle) * .19;
    const y = .19 + Math.cos(angle) * .045;
    fly.add(tube([new THREE.Vector3(x, y, z), new THREE.Vector3(x - .035, y + .09, z * 1.18)], .003, dark));
  }
  fly.scale.setScalar(1.55);
  return fly;
}
