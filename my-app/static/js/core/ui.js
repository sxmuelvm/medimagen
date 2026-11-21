/* Medimagen · se carga en <head> sin defer: marca el documento como "con JavaScript" antes de pintar
   para que el menú móvil no parpadee. Sin este script el menú sigue siendo un bloque normal. */
document.documentElement.classList.add("js");