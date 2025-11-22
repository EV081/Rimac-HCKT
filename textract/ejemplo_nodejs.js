const fs = require('fs');
const https = require('https');

// URL del endpoint (reemplaza con tu URL después del deploy)
const API_URL = 'https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3';

/**
 * Convierte una imagen a base64
 */
function imagenABase64(rutaImagen) {
  const imagen = fs.readFileSync(rutaImagen);
  return imagen.toString('base64');
}

/**
 * Sube una receta médica al sistema
 */
async function subirReceta(nombrePaciente, nombreArchivo, rutaImagen) {
  const imagenBase64 = imagenABase64(rutaImagen);
  
  const payload = JSON.stringify({
    nombre_paciente: nombrePaciente,
    nombre_archivo: nombreArchivo,
    imagen_base64: imagenBase64
  });

  const url = new URL(API_URL);
  
  const options = {
    hostname: url.hostname,
    path: url.pathname,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 200) {
          const resultado = JSON.parse(data);
          console.log('\n✅ Receta subida y analizada exitosamente!\n');
          console.log(`📁 Ubicación: ${resultado.s3.bucket}/${resultado.s3.key}`);
          console.log(`📊 Tamaño: ${resultado.s3.tamaño_bytes} bytes\n`);
          
          const analisis = resultado.analisis;
          console.log(`👨‍⚕️ Doctor: ${analisis.doctor}`);
          console.log(`👤 Paciente: ${analisis.paciente}`);
          console.log(`💊 Total de medicinas: ${analisis.total_medicinas}\n`);
          
          console.log('📋 Medicinas e indicaciones:');
          analisis.medicinas.forEach((medicina, i) => {
            console.log(`\n  ${i + 1}. ${medicina.nombre}`);
            medicina.indicaciones.forEach(indicacion => {
              console.log(`     • ${indicacion}`);
            });
          });
          
          if (analisis.otras_indicaciones) {
            console.log(`\n📝 Otras indicaciones: ${analisis.otras_indicaciones}`);
          }
          
          resolve(resultado);
        } else {
          console.error(`❌ Error: ${res.statusCode}`);
          console.error(data);
          reject(new Error(`HTTP ${res.statusCode}`));
        }
      });
    });
    
    req.on('error', (error) => {
      console.error('❌ Error en el request:', error);
      reject(error);
    });
    
    req.write(payload);
    req.end();
  });
}

// Ejemplo de uso
subirReceta(
  'Juan_Lopez',
  'imagen_2.png',
  './mi_receta.png'  // Cambia esto por tu imagen
).catch(console.error);
