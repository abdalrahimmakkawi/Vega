using System.Numerics;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;

// Shared rocket component scene -> PicoGK voxel geometry -> binary STL.
try
{
    if(args.Length!=4 || args[0]!="rocket")throw new ArgumentException("Usage: Vega.Native rocket <scene.json> <output.stl> <voxel-mm>");
    float pitch=float.Parse(args[3],System.Globalization.CultureInfo.InvariantCulture);
    if(!float.IsFinite(pitch)||pitch<.5f||pitch>2f)throw new ArgumentException("Voxel pitch must be 0.5–2 mm");
    using var document=JsonDocument.Parse(File.ReadAllText(args[1]));
    var recipe=document.RootElement.GetProperty("geometry_recipe");
    var profile=recipe.GetProperty("profile_mm").EnumerateArray().Select(p=>p.EnumerateArray().Select(n=>n.GetSingle()).ToArray()).ToArray();
    float wall=recipe.GetProperty("wall_mm").GetSingle();
    using var library=new Library(pitch);
    Library.RegisterGlobalLibrary(library);
    using var output=new Mesh(library);
    var records=new List<object>();int degenerateRemoved=0;
    var calls=new List<object>{new {library="ShapeKernel",operation="BasePipe.SetRadius / voxConstruct",status="executed"},new {library="PicoGK",operation="voxel construction, clipping and meshing",status="executed"}};
    void Append(Voxels voxels,string id,string name)
    {
        using var remeshed=voxels.mshAsMesh();
        if(remeshed.nTriangleCount()==0)throw new ArgumentException("Empty native component");
        int nativeStart=output.nTriangleCount();
        for(int i=0;i<remeshed.nTriangleCount();i++)
        {
            remeshed.GetTriangle(i,out Vector3 a,out Vector3 b,out Vector3 c);
            float areaSquared=Vector3.Cross(b-a,c-a).LengthSquared();
            if(!float.IsFinite(areaSquared))throw new ArgumentException("Nonfinite PicoGK geometry");
            if(areaSquared==0){degenerateRemoved++;continue;}
            output.nAddTriangle(a,b,c);
        }
        if(output.nTriangleCount()==nativeStart)throw new ArgumentException("No nondegenerate component triangles");
        records.Add(new {component_id=id,name=name,first_triangle=nativeStart,triangle_count=output.nTriangleCount()-nativeStart});
    }
    if(wall<2*pitch)throw new ArgumentException("Wall needs at least two voxels");
    bool hasCooling=recipe.TryGetProperty("cooling",out var cooling);
    using var cutter=hasCooling?Passages.Sweep(Passages.Routes(cooling),cooling.GetProperty("radius_mm").GetSingle()):new Voxels();
    using var assembly=new Voxels();
    using var feedBodies=new Voxels();
    using var feedBores=new Voxels();
    int centerlineSamples=0,feedCenterlineSamples=0;
    foreach(var part in recipe.GetProperty("components").EnumerateArray())
    {
        int first=part.GetProperty("profile_indices")[0].GetInt32();
        int last=part.GetProperty("profile_indices")[1].GetInt32();
        var a=profile[first];var b=profile[last];
        float RadiusAt(float z)
        {
            for(int i=first;i<last;i++)
            {
                var lo=profile[i];var hi=profile[i+1];
                if(z<=hi[0] || i==last-1)return lo[1]+(hi[1]-lo[1])*(z-lo[0])/(hi[0]-lo[0]);
            }
            throw new ArgumentException("Invalid shared nozzle profile");
        }
        var pipe=new BasePipe(new LocalFrame(new Vector3(0,0,a[0])),b[0]-a[0],a[1],a[1]+wall);
        pipe.SetRadius(new SurfaceModulation((phi,t)=>RadiusAt(a[0]+t*(b[0]-a[0]))),new SurfaceModulation((phi,t)=>RadiusAt(a[0]+t*(b[0]-a[0]))+wall));
        pipe.SetPolarSteps(192);pipe.SetLengthSteps((uint)Math.Max(32,(int)MathF.Ceiling((b[0]-a[0])/2)));
        using var voxels=pipe.voxConstruct();
        if(hasCooling)voxels.BoolSubtract(cutter);
        assembly.BoolAdd(voxels);Append(voxels,part.GetProperty("id").GetString()!,part.GetProperty("name").GetString()!);
    }
    if(recipe.TryGetProperty("systems",out var systems))
    {
        foreach(var tank in systems.GetProperty("tanks").EnumerateArray())
        {
            var center=tank.GetProperty("center").EnumerateArray().Select(x=>x.GetSingle()).ToArray();
            float length=tank.GetProperty("length_mm").GetSingle(),radius=tank.GetProperty("radius_mm").GetSingle(),tw=tank.GetProperty("wall_mm").GetSingle();
            var outer=new BaseCylinder(new LocalFrame(new Vector3(center[0],center[1],center[2]-length/2)),length,radius+tw);
            var inner=new BaseCylinder(new LocalFrame(new Vector3(center[0],center[1],center[2]-length/2+tw)),length-2*tw,radius);
            outer.SetPolarSteps(128);outer.SetLengthSteps(24);inner.SetPolarSteps(128);inner.SetLengthSteps(24);
            using var voxels=outer.voxConstruct();using var cavity=inner.voxConstruct();voxels.BoolSubtract(cavity);
            feedBodies.BoolAdd(voxels);Append(voxels,tank.GetProperty("id").GetString()!,tank.GetProperty("name").GetString()!);
        }
        foreach(var manifold in systems.GetProperty("manifolds").EnumerateArray())
        {
            using var voxels=Passages.SweepPoints(manifold.GetProperty("points"),manifold.GetProperty("outer_radius_mm").GetSingle());
            var borePoints=manifold.TryGetProperty("bore_points",out var separateBore)?separateBore:manifold.GetProperty("points");
            using var bore=Passages.SweepPoints(borePoints,manifold.GetProperty("bore_radius_mm").GetSingle());
            voxels.BoolSubtract(bore);feedBodies.BoolAdd(voxels);feedBores.BoolAdd(bore);
            Append(voxels,manifold.GetProperty("id").GetString()!,manifold.GetProperty("name").GetString()!);
        }
        var injector=systems.GetProperty("injector");float iz=injector.GetProperty("z_mm").GetSingle(),ir=injector.GetProperty("radius_mm").GetSingle();
        var injectorBody=new BaseCylinder(new LocalFrame(new Vector3(0,0,iz)),injector.GetProperty("length_mm").GetSingle(),ir);
        injectorBody.SetPolarSteps(192);injectorBody.SetLengthSteps(8);
        using(var voxels=injectorBody.voxConstruct())
        {
            foreach(var orifice in injector.GetProperty("orifices").EnumerateArray())
            {
                using var bore=Passages.SweepPoints(orifice.GetProperty("points"),orifice.GetProperty("radius_mm").GetSingle());
                voxels.BoolSubtract(bore);feedBores.BoolAdd(bore);
            }
            feedBodies.BoolAdd(voxels);Append(voxels,"injector_head","Injector face and outlets");
        }
        feedBodies.Fillet(2f);
        feedBodies.BoolSubtract(feedBores);
        assembly.BoolAdd(feedBodies);
        calls.Add(new {library="ShapeKernel + PicoGK",operation="sized capped pressure-fed tanks, independently extended feed bores, injector face and two outlet orifices",status="executed"});
    }
    // The ribs follow the pressure shell. Their density and size are explicit layout
    // assumptions; no topology or thermal optimization has been run.
    {
        // Cross the outer pressure-shell surface by more than one voxel so these
        // supports actually fuse into the shell instead of floating beside it.
        float chamberRadius=profile[0][1],ribRadius=chamberRadius+wall+0.25f,start=8f,end=profile[1][0]-8f;
        using var lattice=new Lattice();
        const int ribCount=24,ringCount=5;
        for(int k=0;k<ribCount;k++)
        {
            var points=new List<Vector3>();
            for(int j=0;j<ringCount;j++)
            {
                float z=start+(end-start)*j/(ringCount-1),a=2*MathF.PI*k/ribCount+0.18f*j;
                points.Add(new Vector3(ribRadius*MathF.Cos(a),ribRadius*MathF.Sin(a),z));
            }
            for(int j=1;j<points.Count;j++)lattice.AddBeam(points[j-1],1.4f,points[j],1.4f);
        }
        for(int j=0;j<ringCount;j++)
        {
            float z=start+(end-start)*j/(ringCount-1);
            for(int k=0;k<ribCount;k++)
            {
                float a=2*MathF.PI*k/ribCount,b=2*MathF.PI*(k+1)/ribCount;
                lattice.AddBeam(new Vector3(ribRadius*MathF.Cos(a),ribRadius*MathF.Sin(a),z),1.4f,new Vector3(ribRadius*MathF.Cos(b),ribRadius*MathF.Sin(b),z),1.4f);
            }
        }
        using var thermal=new Voxels(lattice);assembly.BoolAdd(thermal);Append(thermal,"thermal_lattice","Integrated thermal lattice");
        calls.Add(new {library="PicoGK",operation="24 helical thermal ribs + 5 annular collectors integrated with chamber",status="executed"});
    }
    if(recipe.TryGetProperty("jacket",out var jacket) && jacket.GetProperty("pattern").GetString()!="none")
    {
        using var voxels=Jacket.Build(jacket,calls);
        voxels.Fillet(2f);
        assembly.BoolAdd(voxels);
        assembly.Fillet(2f);
        if(hasCooling)assembly.BoolSubtract(cutter);
        assembly.BoolSubtract(feedBores);
        Append(voxels,"jacket","Experimental outer jacket");
        calls.Add(new {library="PicoGK",operation="2 mm offset closure after bounded jacket union; passages are recut",status="executed"});
    }
    if(hasCooling)
    {
        float bore=cooling.GetProperty("radius_mm").GetSingle();
        centerlineSamples=Passages.CheckCenterlines(assembly,cooling);
        foreach(var port in cooling.GetProperty("ports").EnumerateArray())
        {
            using var tube=Passages.Sweep(new[]{port},bore+cooling.GetProperty("tube_wall_mm").GetSingle());
            tube.BoolSubtract(cutter);
            // Retain only the externally protruding portion; avoid duplicate material inside the shell.
            tube.BoolSubtract(assembly);
            assembly.BoolAdd(tube);
            Append(tube,port.GetProperty("id").GetString()!,port.GetProperty("name").GetString()!);
        }
        using var flowMesh=cutter.mshAsMesh();flowMesh.SaveToStlFile(Path.GetFullPath(args[2])+".flow.stl");
        calls.Add(new {library="PicoGK",operation="shared passage sweeps, wall subtraction, hollow ports and sampled centerline checks",status="executed"});
    }
    assembly.BoolSubtract(cutter);
    assembly.BoolSubtract(feedBores);
    int ligamentSamples=0,ligamentFailures=0;
    if(hasCooling)
    {
        (ligamentSamples,ligamentFailures)=Passages.CheckRadialLigaments(
            assembly,cooling,recipe.GetProperty("minimum_ligament_mm").GetSingle(),pitch);
        calls.Add(new {library="PicoGK",operation="sampled radial pressure-wall ligaments along every cooling channel",status=ligamentFailures==0?"screen_pass":"screen_failed"});
    }
    if(recipe.TryGetProperty("systems",out var routedSystems))
    {
        foreach(var manifold in routedSystems.GetProperty("manifolds").EnumerateArray())
            feedCenterlineSamples+=Passages.CheckPoints(assembly,manifold.GetProperty("bore_points"),manifold.GetProperty("id").GetString()!);
        foreach(var orifice in routedSystems.GetProperty("injector").GetProperty("orifices").EnumerateArray())
            feedCenterlineSamples+=Passages.CheckPoints(assembly,orifice.GetProperty("points"),orifice.GetProperty("id").GetString()!);
        calls.Add(new {library="PicoGK",operation="sampled tank-to-chamber feed and injector centerlines after final booleans",status="executed"});
    }
    output.SaveToStlFile(Path.GetFullPath(args[2])+".scene.stl");
    using var merged=assembly.mshAsMesh();
    if(merged.nTriangleCount()==0)throw new ArgumentException("Empty unioned engine solid");
    using var solidOutput=new Mesh(library);
    int mergedTrianglesRemoved=0;
    for(int i=0;i<merged.nTriangleCount();i++)
    {
        merged.GetTriangle(i,out Vector3 a,out Vector3 b,out Vector3 c);
        float areaSquared=Vector3.Cross(b-a,c-a).LengthSquared();
        if(!float.IsFinite(areaSquared)||areaSquared==0){mergedTrianglesRemoved++;continue;}
        solidOutput.nAddTriangle(a,b,c);
    }
    if(solidOutput.nTriangleCount()==0 || mergedTrianglesRemoved>merged.nTriangleCount()/200)
        throw new ArgumentException("PicoGK union produced too many invalid triangles");
    solidOutput.SaveToStlFile(Path.GetFullPath(args[2]));
    calls.Add(new {library="PicoGK",operation="boolean union of all engine bodies and final solid remesh",status="executed"});
    var checks=new {backend="PicoGK",voxel_pitch_mm=pitch,bodies=records,library_execution=calls,degenerate_triangles_removed=degenerateRemoved,merged_invalid_triangles_removed=mergedTrianglesRemoved,merged_triangles=solidOutput.nTriangleCount(),scene_triangles=output.nTriangleCount(),passage_centerline_samples=centerlineSamples,feed_centerline_samples=feedCenterlineSamples,radial_ligament_samples=ligamentSamples,radial_ligament_failures=ligamentFailures,passage_check=hasCooling?"sampled centerlines clear in pressure shell and ports":"not_requested",limitations="This is concept geometry. Route and ligament sampling do not establish leak-tightness, minimum wall throughout, hydraulic performance, structural integrity, or manufacturability. Injector atomization, valve/regulator hardware, combustion stability and hot-fire validation remain unresolved."};
    File.WriteAllText(args[2]+".checks.json",JsonSerializer.Serialize(checks));
    Console.WriteLine(JsonSerializer.Serialize(checks));
    Library.UnregisterGlobalLibrary();
}
catch(Exception error){Console.Error.WriteLine(error);Environment.ExitCode=1;}
