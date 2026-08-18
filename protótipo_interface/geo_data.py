"""
geo_data.py
============
Camada de dados geográficos do GreenSense.

Responsável por:
- Ler os arquivos .kmz reais (marcos de KM + áreas de roçada) da pasta data/
- Extrair coordenadas e metadados sem depender de bibliotecas externas de KML
  (KMZ é só um .zip contendo um .kml — usamos zipfile + xml padrão do Python)
- Se os KMZ ainda não estiverem disponíveis, cair para um conjunto de dados
  de demonstração no MESMO formato, para o app nunca quebrar.

Quando você colocar os arquivos reais em data/ (qualquer nome, desde que
contenha "km"/"marco" para os marcos e "rocada"/"classificacao" para as
áreas), o app passa a usar os dados reais automaticamente — não precisa
mexer em mais nada.
"""

from __future__ import annotations

import glob
import math
import os
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ============================================================
# ESTRUTURAS
# ============================================================

@dataclass
class MarcoKM:
    nome: str
    lat: float
    lon: float
    km_label: str = ""
    sentido: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class AreaRocada:
    nome: str
    tipo: str  # "ponto", "poligono" ou "linha"
    centroid_lat: float
    centroid_lon: float
    coords: list = field(default_factory=list)  # lista de (lat, lon)
    classificacao: str = ""  # ex.: alta/média/baixa, se vier no KMZ
    extra: dict = field(default_factory=dict)


@dataclass
class GeoDataset:
    marcos: list  # list[MarcoKM]
    areas_rocada: list  # list[AreaRocada]
    fonte_real: bool  # True se veio de KMZ real, False se é demonstração
    arquivos_usados: list = field(default_factory=list)


# ============================================================
# LEITURA DE KMZ / KML (sem dependências externas)
# ============================================================

def _local_tag(tag: str) -> str:
    """Remove o namespace do XML, ex: '{http://...}Placemark' -> 'Placemark'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _parse_coord_string(text: str):
    """Converte uma string de coordenadas KML 'lon,lat,alt lon,lat,alt ...'
    em uma lista de tuplas (lat, lon)."""
    coords = []
    for chunk in text.strip().split():
        partes = chunk.split(",")
        if len(partes) >= 2:
            try:
                lon, lat = float(partes[0]), float(partes[1])
                coords.append((lat, lon))
            except ValueError:
                continue
    return coords


def _centroid(coords):
    if not coords:
        return None
    lat_media = sum(c[0] for c in coords) / len(coords)
    lon_media = sum(c[1] for c in coords) / len(coords)
    return (lat_media, lon_media)


def _find_first(elem, local_names):
    """Busca recursiva pelo primeiro filho cujo tag (sem namespace) esteja em local_names."""
    for child in elem.iter():
        if _local_tag(child.tag) in local_names:
            return child
    return None


def _construir_mapa_pais(root):
    return {filho: pai for pai in root.iter() for filho in pai}


def _nome_pasta_ancestral(pm, mapa_pais):
    """Sobe na árvore até achar o nome da Folder/Document que contém o
    Placemark — usado para classificar corretamente quando marcos e áreas
    de roçada estão misturados no mesmo arquivo .kmz, em pastas diferentes."""
    atual = pm
    while atual in mapa_pais:
        atual = mapa_pais[atual]
        if _local_tag(atual.tag) in ("Folder", "Document"):
            for child in atual:
                if _local_tag(child.tag) == "name" and child.text:
                    return child.text.strip().lower()
    return ""


def _extract_placemarks(xml_bytes):
    """Extrai todos os Placemarks de um KML, ignorando namespace."""
    root = ET.fromstring(xml_bytes)
    mapa_pais = _construir_mapa_pais(root)
    placemarks = []

    for pm in root.iter():
        if _local_tag(pm.tag) != "Placemark":
            continue

        nome_pasta = _nome_pasta_ancestral(pm, mapa_pais)
        nome, descricao = "", ""
        for child in pm:
            lt = _local_tag(child.tag)
            if lt == "name" and child.text:
                nome = child.text.strip()
            elif lt == "description" and child.text:
                descricao = child.text.strip()

        extended = {}
        for data_el in pm.iter():
            if _local_tag(data_el.tag) == "Data":
                key = data_el.get("name")
                val_el = _find_first(data_el, {"value"})
                if key and val_el is not None and val_el.text:
                    extended[key] = val_el.text.strip()
            if _local_tag(data_el.tag) == "SimpleData":
                key = data_el.get("name")
                if key and data_el.text:
                    extended[key] = data_el.text.strip()

        ponto_el = _find_first(pm, {"Point"})
        poligono_el = _find_first(pm, {"Polygon"})
        linha_el = _find_first(pm, {"LineString"})

        entrada = {"nome": nome, "descricao": descricao, "extended": extended, "pasta": nome_pasta}

        if ponto_el is not None:
            coord_el = _find_first(ponto_el, {"coordinates"})
            if coord_el is not None and coord_el.text:
                pares = _parse_coord_string(coord_el.text)
                if pares:
                    entrada["tipo"] = "ponto"
                    entrada["lat"], entrada["lon"] = pares[0]
                    placemarks.append(entrada)
                    continue

        if poligono_el is not None:
            coord_el = _find_first(poligono_el, {"coordinates"})
            if coord_el is not None and coord_el.text:
                coords = _parse_coord_string(coord_el.text)
                if coords:
                    entrada["tipo"] = "poligono"
                    entrada["coords"] = coords
                    entrada["centroid"] = _centroid(coords)
                    placemarks.append(entrada)
                    continue

        if linha_el is not None:
            coord_el = _find_first(linha_el, {"coordinates"})
            if coord_el is not None and coord_el.text:
                coords = _parse_coord_string(coord_el.text)
                if coords:
                    entrada["tipo"] = "linha"
                    entrada["coords"] = coords
                    entrada["centroid"] = _centroid(coords)
                    placemarks.append(entrada)

    return placemarks


def _read_kml_bytes_from_kmz(caminho_kmz):
    with zipfile.ZipFile(caminho_kmz) as z:
        nomes_kml = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not nomes_kml:
            return None
        # Prioriza doc.kml se existir (padrão do Google Earth)
        nomes_kml.sort(key=lambda n: 0 if os.path.basename(n).lower() == "doc.kml" else 1)
        return z.read(nomes_kml[0])


def _carregar_placemarks(caminho_arquivo):
    """Aceita KMZ normal, KML e também KML puro salvo incorretamente como .kmz."""
    xml_bytes = None

    if caminho_arquivo.lower().endswith(".kmz"):
        try:
            xml_bytes = _read_kml_bytes_from_kmz(caminho_arquivo)
        except (zipfile.BadZipFile, OSError):
            # Alguns arquivos entregues no challenge têm extensão .kmz,
            # mas o conteúdo é XML/KML puro. Nesse caso, lê como KML.
            with open(caminho_arquivo, "rb") as f:
                xml_bytes = f.read()
    else:
        with open(caminho_arquivo, "rb") as f:
            xml_bytes = f.read()

    if not xml_bytes:
        return []

    try:
        return _extract_placemarks(xml_bytes)
    except ET.ParseError:
        return []


# ============================================================
# CLASSIFICAÇÃO DOS ARQUIVOS EM data/
# ============================================================

def _listar_arquivos_geo():
    padroes = ("*.kmz", "*.kml")
    arquivos = []
    for padrao in padroes:
        arquivos.extend(glob.glob(os.path.join(DATA_DIR, padrao)))
    return sorted(arquivos)


def _classificar_arquivo(caminho):
    nome = os.path.basename(caminho).lower()
    if "rocada" in nome or "roçada" in nome or "classific" in nome:
        return "rocada"
    if "km" in nome or "marco" in nome:
        return "km"
    return "desconhecido"


def _classificar_placemark(pm, categoria_arquivo):
    """Decide se um placemark é um marco de KM ou uma área de roçada.
    Prioridade: 1) nome da pasta/Folder dentro do KML, 2) categoria do
    arquivo, 3) tipo de geometria (polígono/linha nunca é marco)."""
    pasta = pm.get("pasta", "")
    if "rocada" in pasta or "roçada" in pasta or "classific" in pasta:
        return "rocada"
    if "km" in pasta or "marco" in pasta:
        return "km" if pm.get("tipo") == "ponto" else "rocada"

    if pm.get("tipo") != "ponto":
        return "rocada"

    if categoria_arquivo in ("km", "rocada"):
        return categoria_arquivo

    return "km"  # ponto solto sem pista melhor: assume marco


# ============================================================
# EXTRAÇÃO DE NÚMERO DE KM A PARTIR DO NOME/DESCRIÇÃO
# ============================================================

def _extrair_km_label(nome, descricao):
    import re

    texto = f"{nome} {descricao}"
    match = re.search(r"km[\s\.:]*?(\d{1,3})[\+\.]?(\d{0,3})", texto, re.IGNORECASE)
    if match:
        inteiro = match.group(1)
        decimal = match.group(2) or "000"
        return f"KM {int(inteiro):03d}+{decimal.ljust(3, '0')[:3]}"
    return nome or "KM ?"


# ============================================================
# CARREGAMENTO PRINCIPAL
# ============================================================

def carregar_dados_geograficos() -> GeoDataset:
    arquivos = _listar_arquivos_geo()

    if not arquivos:
        return _dataset_demo()

    marcos, areas = [], []
    usados = []

    for caminho in arquivos:
        categoria = _classificar_arquivo(caminho)
        placemarks = _carregar_placemarks(caminho)
        if not placemarks:
            continue
        usados.append(os.path.basename(caminho))

        for pm in placemarks:
            # Classifica por placemark (não por arquivo inteiro), usando a
            # pasta do KML como pista principal — isso resolve o caso comum
            # de marcos e áreas de roçada misturados no mesmo .kmz.
            classe_pm = _classificar_placemark(pm, categoria)
            eh_marco = classe_pm == "km"

            if eh_marco:
                lat, lon = pm["lat"], pm["lon"]
                marcos.append(
                    MarcoKM(
                        nome=pm["nome"] or "Marco",
                        lat=lat,
                        lon=lon,
                        km_label=_extrair_km_label(pm["nome"], pm["descricao"]),
                        sentido=pm["extended"].get("sentido", pm["extended"].get("Sentido", "")),
                        extra=pm["extended"],
                    )
                )
            else:
                if pm.get("tipo") == "ponto":
                    centro = (pm["lat"], pm["lon"])
                    coords = [centro]
                else:
                    coords = pm.get("coords", [])
                    centro = pm.get("centroid")
                if not centro:
                    continue

                areas.append(
                    AreaRocada(
                        nome=pm["nome"] or "Área de roçada",
                        tipo=pm.get("tipo", "ponto"),
                        centroid_lat=centro[0],
                        centroid_lon=centro[1],
                        coords=coords,
                        classificacao=pm["extended"].get(
                            "classificacao", pm["extended"].get("Classificacao", "")
                        ),
                        extra=pm["extended"],
                    )
                )

    if not marcos and not areas:
        return _dataset_demo()

    return GeoDataset(marcos=marcos, areas_rocada=areas, fonte_real=True, arquivos_usados=usados)


# ============================================================
# DADOS DE DEMONSTRAÇÃO (mesmo formato, coordenadas plausíveis
# ao longo de um traçado fictício — só usado se não houver KMZ)
# ============================================================

def _dataset_demo() -> GeoDataset:
    lat0, lon0 = -23.45, -46.65
    marcos = []
    for i in range(18):
        marcos.append(
            MarcoKM(
                nome=f"Marco demonstrativo {i + 1}",
                lat=lat0 - i * 0.021,
                lon=lon0 - i * 0.018,
                km_label=f"KM {i * 10:03d}+000",
                sentido="Norte" if i % 2 == 0 else "Sul",
                extra={"demo": "true"},
            )
        )

    areas = []
    for i in range(24):
        clat = lat0 - (i * 0.75) * 0.021 + 0.006
        clon = lon0 - (i * 0.75) * 0.018 - 0.004
        areas.append(
            AreaRocada(
                nome=f"Área de roçada demonstrativa {i + 1}",
                tipo="ponto",
                centroid_lat=clat,
                centroid_lon=clon,
                coords=[(clat, clon)],
                classificacao="média",
                extra={"demo": "true"},
            )
        )

    return GeoDataset(marcos=marcos, areas_rocada=areas, fonte_real=False, arquivos_usados=[])


# ============================================================
# UTILITÁRIOS GEOGRÁFICOS
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def distancia_area_rocada_mais_proxima(lat, lon, areas_rocada):
    """Retorna (distancia_km, area) da área de roçada mais próxima de um ponto."""
    if not areas_rocada:
        return None, None
    melhor_dist, melhor_area = None, None
    for area in areas_rocada:
        d = haversine_km(lat, lon, area.centroid_lat, area.centroid_lon)
        if melhor_dist is None or d < melhor_dist:
            melhor_dist, melhor_area = d, area
    return melhor_dist, melhor_area
