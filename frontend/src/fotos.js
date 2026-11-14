// Fotografías de Santa Marta tomadas de Wikimedia Commons, con licencias libres.
// Se cargan directamente desde Commons (Special:FilePath) y sus créditos se muestran en /creditos,
// como exigen las licencias CC BY y CC BY-SA.
const BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/";

export const FOTOS = {
  marina: {
    archivo: "2018 Santa Marta (Colombia) - La marina desde el Camellón Rodrigo de Bastidas.jpg",
    lugar: "La marina desde el Camellón Rodrigo de Bastidas", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  marinaBarcos: {
    archivo: "2018 Santa Marta (Colombia) - Barcos frente en la marina de Santa Marta.jpg",
    lugar: "Barcos en la marina", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  rodadero: {
    archivo: "Vista general de la playa de El Rodadero.jpg",
    lugar: "Playa de El Rodadero", autor: "Sheisale", licencia: "CC BY-SA 4.0",
  },
  rodaderoCalle: {
    archivo: "2021 Santa Marta - El Rodadero, calle 6 con carrera 11 A.jpg",
    lugar: "El Rodadero, calle 6 con carrera 11A", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  vistaSierra: {
    archivo: "El Rodadero visto desde la cuchilla de San Lorenzo en la Sierra Nevada de Santa Marta - Flickr - Alejandro Bayer.jpg",
    lugar: "El Rodadero visto desde la Cuchilla de San Lorenzo", autor: "Alejandro Bayer Tamayo", licencia: "CC BY-SA 2.0",
  },
  taganga: {
    archivo: "Bahía de Taganga, Magdalena, Colombia.jpg",
    lugar: "Bahía de Taganga", autor: "Agpinzon01", licencia: "CC BY-SA 4.0",
  },
  peatonal: {
    archivo: "2018 Santa Marta (Colombia) - Peatonal en el Centro Histórico, Calle 19 entre carreras 4 y 5.jpg",
    lugar: "Peatonal de la calle 19, Centro Histórico", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  obras: {
    archivo: "2018 Santa Marta (Colombia) - Calle 13 con carrera 5, obras públicas.jpg",
    lugar: "Obras públicas en la calle 13 con carrera 5", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  catedral: {
    archivo: "2018 Santa Marta (Colombia) - Centro Histórico, Catedral Basílica.jpg",
    lugar: "Catedral Basílica, Centro Histórico", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  casaAzul: {
    archivo: "2019 Santa Marta - Casa azul en el Parque de Los Novios.jpg",
    lugar: "Casa azul en el Parque de Los Novios", autor: "Felipe Restrepo Acosta", licencia: "CC BY-SA 4.0",
  },
  sierra: {
    archivo: "Cuchilla de San Lorenzo, Sierra Nevada de Santa Marta, Magdalena, Colombia.jpg",
    lugar: "Cuchilla de San Lorenzo, Sierra Nevada", autor: "Reduvida3", licencia: "CC BY-SA 4.0",
  },
  atardecer: {
    archivo: "Atardecer de Santa Marta.jpg",
    lugar: "Atardecer en la bahía", autor: "Franciscokarriere", licencia: "CC BY-SA 4.0",
  },
  pelicano: {
    archivo: "Brown Pelican and two Snowy Egrets in Santa Marta Port, Colombia.jpg",
    lugar: "Pelícano y garzas en el puerto", autor: "Reduvida3", licencia: "CC BY-SA 4.0",
  },
};

export function urlFoto(clave, ancho = 1600) {
  return `${BASE}${encodeURIComponent(FOTOS[clave].archivo)}?width=${ancho}`;
}

export function paginaFoto(clave) {
  return `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(FOTOS[clave].archivo.replace(/ /g, "_"))}`;
}
