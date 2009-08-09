xof 0302txt 0032

// Built with Blender 2.45. Exported with Blender2FSX 0.10.


template Header {
  <3D82AB43-62DA-11cf-AB39-0020AF71E433>
  WORD major;
  WORD minor;
  DWORD flags;
}

template GuidToName {
  <7419dfe5-b73a-4d66-98d8-c082591dc9e7>
  STRING Guid;
  STRING Name;
}

template Vector {
  <3D82AB5E-62DA-11cf-AB39-0020AF71E433>
  FLOAT x;
  FLOAT y;
  FLOAT z;
}
template SkinWeight {
  <C3B5EDF9-7345-463d-96D7-6386E2EC4030>
  STRING boneRef;
  FLOAT weight;
}


template SkinWeightGroup {
  <E7B502DB-0C05-4288-A025-80762E19E0AB>
  DWORD nWeights;
  array SkinWeight skinWeights[nWeights];
}


template Coords2d {
  <F6F23F44-7686-11cf-8F52-0040333594A3>
  FLOAT u;
  FLOAT v;
}

template Matrix4x4 {
  <F6F23F45-7686-11cf-8F52-0040333594A3>
  array FLOAT matrix[16];
}

template ColorRGBA {
  <35FF44E0-6C7C-11cf-8F52-0040333594A3>
  FLOAT red;
  FLOAT green;
  FLOAT blue;
  FLOAT alpha;
}

template ColorRGB {
  <D3E16E81-7835-11cf-8F52-0040333594A3>
  FLOAT red;
  FLOAT green;
  FLOAT blue;
}

template TextureFilename {
  <A42790E1-7810-11cf-8F52-0040333594A3>
  STRING filename;
}

template Material {
  <3D82AB4D-62DA-11cf-AB39-0020AF71E433>
  ColorRGBA faceColor;
  FLOAT power;
  ColorRGB specularColor;
  ColorRGB emissiveColor;
  [...]
  }

template MeshFace {
  <3D82AB5F-62DA-11cf-AB39-0020AF71E433>
  DWORD nFaceVertexIndices;
  array DWORD faceVertexIndices[nFaceVertexIndices];
}

template MeshTextureCoords {
  <F6F23F40-7686-11cf-8F52-0040333594A3>
  DWORD nTextureCoords;
  array Coords2d textureCoords[nTextureCoords];
}
template MeshSkinWeights {
  <C7E2131A-30F3-4eb9-AACC-E0AE11D8FE62>
  DWORD nVertices;
  array SkinWeightGroup skinWeights[nVertices];
}

template MeshMaterialList {
  <F6F23F42-7686-11cf-8F52-0040333594A3>
  DWORD nMaterials;
  DWORD nFaceIndexes;
  array DWORD faceIndexes[nFaceIndexes];
  [Material]
  }

template MeshNormals {
  <F6F23F43-7686-11cf-8F52-0040333594A3>
  DWORD nNormals;
  array Vector normals[nNormals];
  DWORD nFaceNormals;
  array MeshFace faceNormals[nFaceNormals];
}

template Mesh {
  <3D82AB44-62DA-11cf-AB39-0020AF71E433>
  DWORD nVertices;
  array Vector vertices[nVertices];
  DWORD nFaces;
  array MeshFace faces[nFaces];
  [...]
  }

template BoneInfo {
  <1FF0AE59-4B0B-4dfe-88F2-91D58E395767>
  STRING boneName;
}

template AnimLinkName {
  <0057EC91-F96B-4f5e-9CFB-0E305F39DA1A>
  STRING linkName;
}

template IKChain {
  <2684B333-AAB2-45d9-87D8-6E2BB22616AD>
  STRING chainName;
  STRING startNode;
  STRING endNode;
}

template ConstraintInfo {
  <8713D495-C538-44dc-AE54-1097E7C93D13>
  Boolean bActive;
  Boolean bLimited;
  FLOAT fUpperLimit;
  FLOAT fLowerLimit;
}

// Note that the exported rotation order is YZX
template JointConstraint {
  <BE433CF1-BCC0-43f8-9FE5-DB0556414426>
  array ConstraintInfo Rotation[3];
  array ConstraintInfo Translation[3];
}

template FrameTransformMatrix {
  <F6F23F41-7686-11cf-8F52-0040333594A3>
  Matrix4x4 frameMatrix;
}

template Frame {
  <3D82AB46-62DA-11cf-AB39-0020AF71E433>
  [...]
}

template FloatKeys {
  <10DD46A9-775B-11cf-8F52-0040333594A3>
  DWORD nValues;
  array FLOAT values[nValues];
}

template TimedFloatKeys {
  <F406B180-7B3B-11cf-8F52-0040333594A3>
  DWORD time;
  FloatKeys tfkeys;
}

template AnimationKey {
  <10DD46A8-775B-11cf-8F52-0040333594A3>
  DWORD keyType;
  DWORD nKeys;
  array TimedFloatKeys keys[nKeys];
}

template AnimationOptions {
  <E2BF56C0-840F-11cf-8F52-0040333594A3>
  DWORD openclosed;
  DWORD positionquality;
}

template Animation {
  <3D82AB4F-62DA-11cf-AB39-0020AF71E433>
  [...]
}

template AnimationSet {
  <3D82AB50-62DA-11cf-AB39-0020AF71E433>
  [Animation]
}

template DiffuseTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07401>
  STRING filename;
}

template SpecularTextureFileName {
  <DF64E0D7-4FFA-4634-9DA0-3EF2FAA081CE>
  STRING filename;
}

template AmbientTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07402>
  STRING filename;
}

template EmissiveTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07403>
  STRING filename;
}

template ReflectionTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07404>
  STRING filename;
}

template ShininessTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07405>
  STRING filename;
}

template BumpTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07406>
  STRING filename;
}

template DisplacementTextureFileName {
  <E00200E2-D4AB-481a-9B85-E20F9AE07407>
  STRING filename;
}

template DetailTextureFileName {
  <C223DC28-5C0E-41bc-9706-A30E023EF118>
  STRING filename;
}

template FresnelTextureFileName {
  <C16742E5-974D-4576-870D-2047C79DF7A9>
  STRING filename;
}

template FS10Material {
  <16B4B490-C327-42e3-8A71-0FA35C817EA2>
  ColorRGBA FallbackDiffuse;
  ColorRGB  Specular;
  FLOAT     Power;
  FLOAT     DetailScale;
  FLOAT     BumpScale;
  FLOAT     EnvironmentLevelScale;
  Boolean   bUseGlobalEnv;
  Boolean   bModEnvInvDiffuseAlpha;
  Boolean   bModEnvSpecularMapAlpha;
  Boolean   bFresnelDiffuse; Boolean bFresnelSpecular; Boolean bFresnelEnvironment;
  Boolean   bUsePrecipitation;
  Boolean   bPrecipOffset;
  FLOAT     PrecipOffset;
  FLOAT     SpecMapPowerScale;
  STRING    SrcBlend;
  STRING    DstBlend;
  [...]
}

template AllowBloom {
  <D66E37C9-9DFE-4092-8565-C6E4C3498235>
  Boolean     AllowBloom;
}

template BloomData {
  <58ED1E67-0D18-44EF-B676-40BB20C1EE88>
  Boolean BloomCopy;
  Boolean BloomModAlpha;
}

template SpecularBloomFloor {
  <21195174-A31D-47ed-BE5A-04ACAD4C3544>
  FLOAT     SpecularBloomFloor;
}

template AmbientLightScale {
  <4CC76AEB-E84F-4688-AB49-E1DC4B9273C7>
  FLOAT     AmbientLightScale;
}

template EmissiveData {
  <A02EF480-3ED3-433d-A71D-5CAC4775757A>
  STRING   EmissiveBlend;
}

template AlphaData {
  <10DB69F3-E0EE-4fb3-8055-63E539EF5885>
  Boolean  ZTestAlpha;
  FLOAT    AlphaTestValue;
  STRING   AlphaTestFunction;
  Boolean  FinalAlphaWrite;
  FLOAT    FinalAlphaWriteValue;
}

template EnhancedParameters {
  <99CAD20D-DCC5-4ad4-ADAE-ED3CDE30CC02>
  Boolean  AssumeVerticalNormal;
  Boolean  ZWriteAlpha;
  Boolean  NoZWrite;
  Boolean  VolumeShadow;
  Boolean  NoShadow;
  Boolean  PrelitVertices;
}

template BaseMaterialSpecular {
  <E294ED4E-5C5A-4927-B19A-6A2D445FAF24>
  Boolean  AllowBaseMaterialSpecular;
}

template BaseMaterialSkin {
  <B640F860-9E28-4cab-AD46-CACCE2A418AC>
  Boolean  AllowSkinning;
}

template DoubleSidedMaterial {
  <B1C6C3B0-DD1A-417b-919A-B04BAD6AE06D>
  Boolean  DoubleSided;
}

template BlendConstantSetting {
  <48EA96C3-588E-451d-B4BB-0C746C8380D9>
  Boolean  BlendConstant;
}

template ForceTextureAddressWrapSetting {
  <046EE84C-7977-4a11-AA2B-C79FF5391EDD>
  Boolean  ForceTextureAddressWrap;
}

template ForceTextureAddressClampSetting {
  <DB108D57-A3A8-4b76-8CB0-8379CDDEC074>
  Boolean  ForceTextureAddressClamp;
}

template NoSpecularBloom {
  <BCE314D2-15DB-4ffd-9F6F-0763B2A4616F>
  Boolean  AllowSpecularBloom;
}

template EmissiveBloom {
  <5FF8D7A2-30B5-41bc-A891-28A427D78246>
  Boolean  AllowEmissiveBloom;
}

template BlendDiffuseByBaseAlpha {
  <A623FA7C-37CB-4d17-B702-854E0DBDB467>
  Boolean  BlendDiffByBaseAlpha;
}

template BlendDiffuseByInverseSpecularMapAlpha {
  <DAA68529-1C27-4182-9D97-E631A4759EA7>
  Boolean  BlendDiffuseByInvSpecAlpha;
}

template NNumberTexture {
  <E49E744A-CDBE-40c1-9C89-4A46BEB44D33>
  Boolean  IsNNumberTexture;
}

template PartData {
  <79B183BA-7E70-44d1-914A-23B304CA91E5>
  DWORD nByteCount;
  array BYTE XMLData[ nByteCount ];
}

Header {
  1;
  0;
  1;
}


GuidToName {
  "{29f7c9d6-caab-4ef8-c401-2d525a12b692}";
  "gmaxTest";
}


// Scene

// Layer 1

Frame frm-gmaxTest_LOD_100 {
  FrameTransformMatrix {
    1.000000, 0.000000, 0.000000, 0.0,
    0.000000, 0.000000, 1.000000, 0.0,
    0.000000, 1.000000, 0.000000, 0.0,
    0.000000, 0.000000, 0.000000, 1.0;;
  }		// End FrameTransformMatrix

  Mesh gmaxTest_LOD_100 {
    18;		// Mesh 'gmaxTest_LOD_100' contains 18 vertices
    -20.360941; -14.316930; 18.616911;,
    11.865080; -14.316930; 18.616911;,
    11.865080; 7.269553; 18.616911;,
    -20.360941; 7.269553; 18.616911;,
    11.865080; -14.316930; 0.000000;,
    11.865080; 7.269553; 0.000000;,
    11.865080; -14.316930; 18.616911;,
    11.865080; 7.269553; 0.000000;,
    -20.360941; 7.269553; 0.000000;,
    -20.360941; 7.269553; 18.616911;,
    11.865080; 7.269553; 18.616911;,
    -20.360941; 7.269553; 0.000000;,
    -20.360941; -14.316930; 0.000000;,
    -20.360941; -14.316930; 18.616911;,
    -20.360941; -14.316930; 18.616911;,
    -20.360941; -14.316930; 0.000000;,
    11.865080; -14.316930; 0.000000;,
    11.865080; -14.316930; 18.616911;;

    10;		// Mesh 'gmaxTest_LOD_100' contains 10 faces
    3; 2, 1, 0;,
    3; 0, 3, 2;,
    3; 2, 5, 4;,
    3; 4, 6, 2;,
    3; 9, 8, 7;,
    3; 7, 10, 9;,
    3; 13, 12, 11;,
    3; 11, 3, 13;,
    3; 16, 15, 14;,
    3; 14, 17, 16;;

    MeshMaterialList {
      2;	// 2 Materials
      10;	// 10 Faces have materials specified
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      1,
      1;

      Material m0 {	// Mat
        0.290196; 0.882353; 0.360784; 1.000000;;
        50.000000;
        0.900000; 0.900000; 0.900000;;
        0.000000; 0.000000; 0.000000;;
        TextureFileName {
          "fs2x-palette.dds";
        }
        DiffuseTextureFileName {
          "fs2x-palette.dds";
        }
        FS10Material {
          0.290196; 0.882353; 0.360784; 1.000000;;	// Diffuse
          0.900000; 0.900000; 0.900000;;	// Specular
          50.000000;		// Specular power
          1.000000; 1.000000;	// Detail and bump scales
          0.200000;		// Scale environment level factor
          0;			// Use global environment
          0;			// Blend env by inv diffuse alpha
          0;			// Blend env by specular map alpha
          0; 0; 0;		// Fresnel: Diffuse, Spec, Env
          0; 0; 0.000000;	// Precipitation: Use, Delay, Offset
          50.000000;		// Specular Map Power Scale
          "One"; "Zero";	// Src/Dest blend

          BlendDiffuseByBaseAlpha {
            0;
          }
          BlendDiffuseByInverseSpecularMapAlpha {
            0;
          }
          AllowBloom {
            1;
          }
          SpecularBloomFloor {
            0.900000;
          }
          EmissiveData {
            "Blend";
          }
          AlphaData {
            0; 0.000000; "Never"; 0; 255.000000;
          }
          EnhancedParameters {
            1; 0; 0; 0; 0; 0;
          }
          BaseMaterialSkin {
            0;
          }
          DoubleSidedMaterial {
            0;
          }
          BlendConstantSetting {
            0;
          }
          ForceTextureAddressWrapSetting {
            0;
          }
          ForceTextureAddressClampSetting {
            0;
          }
          BaseMaterialSpecular {
            1;
          }
          NoSpecularBloom {
            0;
          }
          EmissiveBloom {
            0;
          }
          AmbientLightScale {
            0.900000;
          }
          DiffuseTextureFileName {
            "fs2x-palette.dds";
          }
          SpecularTextureFileName {
            "fs2x-palette.dds";
          }
        }	// End FS10Material
      }		// End Material 'm0'

      Material m1 {	// Maté
        0.581032; 0.240090; 1.000000; 1.000000;;
        50.000000;
        0.900000; 0.900000; 0.000000;;
        0.000000; 0.000000; 0.000000;;
        TextureFileName {
          "palette.dds";
        }
        DiffuseTextureFileName {
          "palette.dds";
        }
        FS10Material {
          0.581032; 0.240090; 1.000000; 1.000000;;	// Diffuse
          0.900000; 0.900000; 0.000000;;	// Specular
          50.000000;		// Specular power
          1.000000; 1.000000;	// Detail and bump scales
          0.200000;		// Scale environment level factor
          0;			// Use global environment
          0;			// Blend env by inv diffuse alpha
          0;			// Blend env by specular map alpha
          0; 0; 0;		// Fresnel: Diffuse, Spec, Env
          0; 0; 0.000000;	// Precipitation: Use, Delay, Offset
          50.000000;		// Specular Map Power Scale
          "One"; "Zero";	// Src/Dest blend

          BlendDiffuseByBaseAlpha {
            0;
          }
          BlendDiffuseByInverseSpecularMapAlpha {
            0;
          }
          AllowBloom {
            1;
          }
          SpecularBloomFloor {
            0.900000;
          }
          EmissiveData {
            "Blend";
          }
          AlphaData {
            0; 0.000000; "Never"; 0; 255.000000;
          }
          EnhancedParameters {
            1; 0; 0; 0; 0; 0;
          }
          BaseMaterialSkin {
            0;
          }
          DoubleSidedMaterial {
            0;
          }
          BlendConstantSetting {
            0;
          }
          ForceTextureAddressWrapSetting {
            0;
          }
          ForceTextureAddressClampSetting {
            0;
          }
          BaseMaterialSpecular {
            1;
          }
          NoSpecularBloom {
            0;
          }
          EmissiveBloom {
            0;
          }
          AmbientLightScale {
            0.900000;
          }
          DiffuseTextureFileName {
            "palette.dds";
          }
          SpecularTextureFileName {
            "palette.dds";
          }
        }	// End FS10Material
      }		// End Material 'm1'

    }		// End MaterialList for 'gmaxTest_LOD_100'

    MeshNormals {	// Mesh normals for gmaxTest_LOD_100
      5;		// 5 vertex normals
      0.000000; 0.000000; 1.000000;,
      1.000000; 0.000000; 0.000000;,
      0.000000; 1.000000; 0.000000;,
      -1.000000; 0.000000; 0.000000;,
      0.000000; -1.000000; 0.000000;;

      10;		// 10 faces with normals
      3; 0, 0, 0;,
      3; 0, 0, 0;,
      3; 1, 1, 1;,
      3; 1, 1, 1;,
      3; 2, 2, 2;,
      3; 2, 2, 2;,
      3; 3, 3, 3;,
      3; 3, 3, 3;,
      3; 4, 4, 4;,
      3; 4, 4, 4;;
    }		// End Mesh normals for 'gmaxTest_LOD_100'

    MeshTextureCoords {
      18;		// 18 uv pairs
      0.000000; 0.000000;,
      1.000000; 0.000000;,
      1.000000; 1.000000;,
      0.000000; 1.000000;,
      0.000000; 0.000000;,
      1.000000; 0.000000;,
      0.000000; 1.000000;,
      0.000000; 0.000000;,
      1.000000; 0.000000;,
      1.000000; 1.000000;,
      0.000000; 1.000000;,
      0.000000; 0.000000;,
      1.000000; 0.000000;,
      1.000000; 1.000000;,
      0.000000; 1.000000;,
      0.000000; 0.000000;,
      1.000000; 0.000000;,
      1.000000; 1.000000;;
    }		// End MeshTexture Coords for 'gmaxTest_LOD_100'
  }		// End of Mesh 'gmaxTest_LOD_100'
}		// End of frame frm-gmaxTest_LOD_100

