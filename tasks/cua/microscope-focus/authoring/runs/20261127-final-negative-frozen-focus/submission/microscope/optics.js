// Cartesian convention: +Y follows light; s = objectY - lensY.
export function lens(s, f) {
  if (Math.abs(s) < 1e-10) return {kind:'no-finite-image',s,v:null,m:null};
  if (Math.abs(s+f) < 1e-9) return {kind:'infinity',s,v:null,m:null};
  const v=f*s/(s+f);
  return {kind:v>0?'real':'virtual',s,v,m:v/s};
}
export function compute(stageY, objectiveY, eyeY, height=0.05) {
  const objective=lens(stageY-objectiveY,4);
  if(objective.v===null) return {objective,eyepiece:{kind:'no-finite-image',s:null,v:null,m:null},total:null,height:null,orientation:'undefined'};
  const eyepiece=lens(objectiveY+objective.v-eyeY,25);
  const total=eyepiece.m===null?null:objective.m*eyepiece.m;
  return {objective,eyepiece,total,height:total===null?null:height*total,orientation:total===null?'undefined':total<0?'inverted':'upright'};
}
