import xml.etree.ElementTree as ET
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

def leverage_tmx_into_xliff(tmx_file: str, xliff_file: str) -> Tuple[str, Dict[str, int]]:
    """
    Leverage translations from TMX into XLIFF and return statistics
    """
    try:
        logger.info(f"Starting translation leverage from {tmx_file} to {xliff_file}")
        
        # Parse TMX file
        tmx_tree = ET.parse(tmx_file)
        tmx_root = tmx_tree.getroot()
        
        # Create dictionary of source->target translations from TMX
        translations = {}
        translation_count = 0
        
        # XML namespace for xml:lang attribute
        ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}
        
        for tu in tmx_root.findall('.//tu'):
            source_seg = tu.find("./tuv[@xml:lang='en-us']/seg", ns)
            target_seg = tu.find("./tuv[@xml:lang='fr-ca']/seg", ns)
            
            if source_seg is not None and target_seg is not None:
                translations[source_seg.text] = target_seg.text
                translation_count += 1
        
        logger.info(f"Found {translation_count} translations in TMX file")

        # Parse XLIFF file
        xliff_tree = ET.parse(xliff_file)
        xliff_root = xliff_tree.getroot()
        
        # Find all trans-units
        updates_made = 0
        empty_segments = 0
        
        for unit in xliff_root.findall('.//ns0:unit', {'ns0': 'urn:oasis:names:tc:xliff:document:2.0'}):
            source = unit.find('.//ns0:source', {'ns0': 'urn:oasis:names:tc:xliff:document:2.0'})
            target = unit.find('.//ns0:target', {'ns0': 'urn:oasis:names:tc:xliff:document:2.0'})
            
            if source is not None and target is not None:
                if not target.text:  # Empty target
                    empty_segments += 1
                    if source.text in translations:
                        target.text = translations[source.text]
                        updates_made += 1
                        empty_segments -= 1
        
        # Write the modified XLIFF to a new file
        output_file = xliff_file.replace('.xlf', '_leveraged.xlf')
        xliff_tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        stats = {
            'translations_found': translation_count,
            'updates_made': updates_made,
            'remaining_empty': empty_segments
        }
        
        logger.info(f"Leverage complete. Stats: {stats}")
        return output_file, stats
        
    except Exception as e:
        logger.error(f"Error in leverage_tmx_into_xliff: {e}")
        raise

def check_empty_targets(xliff_file: str) -> Dict[str, int]:
    """
    Check for empty target segments in XLIFF file
    """
    try:
        logger.info(f"Checking for empty target segments in {xliff_file}")
        
        xliff_tree = ET.parse(xliff_file)
        xliff_root = xliff_tree.getroot()
        
        empty_count = 0
        total_segments = 0
        
        for unit in xliff_root.findall('.//ns0:unit', {'ns0': 'urn:oasis:names:tc:xliff:document:2.0'}):
            source = unit.find('.//ns0:source', {'ns0': 'urn:oasis:names:tc:xliff:document:2.0'})
            target = unit.find('.//ns0:target', {'ns0': 'urn:oasis:names:tc:xliff:document:2.0'})
            
            if source is not None and target is not None:
                total_segments += 1
                if not target.text:
                    empty_count += 1
        
        stats = {
            'total_segments': total_segments,
            'empty_segments': empty_count,
            'completion_rate': round((total_segments - empty_count) / total_segments * 100, 2)
        }
        
        logger.info(f"XLIFF check complete. Stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error in check_empty_targets: {e}")
        raise 