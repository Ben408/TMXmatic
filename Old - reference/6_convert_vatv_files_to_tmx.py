import PythonTmx
from datetime import datetime
import glob
import csv

language_codes = {  "Arabic_VATV": "ar-SA",                             #Every file name was mapped to its corresponding
                    "Bulgarian (Bulgaria)_VATV": "bg-BG",               #language code, in order to generate the target
                    "Croatian (Croatia)_VATV": "hr-HR",                 #TUV correctly. If more languages are added, or 
                    "Czech (Czechia)_VATV": "cs-CZ",                    #if a new file nomenclature is used, this dictionary
                    "Danish (Denmark)_VATV": "da-DK",                   #must be updated, or replaced entirely.
                    "Dutch (Netherlands)_VATV": "nl-NL", 
                    "Estonian (Estonia)_VATV": "et-EE", 
                    "Finnish (Finland)_VATV": "fi-FI", 
                    "French (Canada)_VATV": "fr-CA", 
                    "French (France)_VATV": "fr-FR", 
                    "German (Germany)_VATV": "de-DE", 
                    "Greek (Greece)_VATV": "el-GR", 
                    "Hebrew (Israel)_VATV": "he-IL", 
                    "Hungarian (Hungary)_VATV": "hu-HU", 
                    "Indonesian (Indonesia)⛑_VATV": "id-ID", 
                    "Italian (Italy)_VATV": "it-IT", 
                    "Japanese (Japan)_VATV": "ja-JP", 
                    "Korean (Korea)_VATV": "ko-KR", 
                    "Latvian (Latvia)_VATV": "lv-LV", 
                    "Lithuanian (Lithuania)_VATV": "lt-LT", 
                    "Malay (Malaysia)_VATV": "ms-MY", 
                    "Mongolian (Mongolia)_VATV": "mn-MN", 
                    "Norwegian (Norway)_VATV": "nb-NO", 
                    "Polish (Poland)_VATV": "pl-PL", 
                    "Portuguese (Brazil)_VATV": "pt-BR", 
                    "Romanian (Romania)_VATV": "ro-RO", 
                    "Russian (Russia)_VATV": "ru-RU", 
                    "Serbian (Serbia)_VATV": "sr-Cyrl-RS", 
                    "Simplified Chinese_VATV": "zh-CN", 
                    "Slovak (Slovakia)_VATV": "sk-SK", 
                    "Slovenian (Slovenia)_VATV": "sl-SI", 
                    "Spanish (Latin America)_VATV": "es-419", 
                    "Spanish (Neutral)_VATV": "es-ES", 
                    "Swedish (Sweden)_VATV": "sv-SE", 
                    "Thai (Thailand)_VATV": "th-TH", 
                    "Traditional Chinese (Hong Kong)_VATV": "zh-HK", 
                    "Traditional Chinese_VATV": "zh-TW", 
                    "Turkish (Türkiye)_VATV": "tr-TR", 
                    "Ukrainian (Ukraine)_VATV": "uk-UA", 
                    "Vietnamese (Vietnam)_VATV": "vi-VN" 
                    }


def csv_converter(csv_file, target_lang):
    """
    csv_converter(csv_file:DictReader, target_lang:str)->list
    
    Converts a CSV file into a TMX file, using only the source
      and target information, located under "Base Value" and 
      "Translated Value" columns
    
    :param csv_file: A DictReader created from a CSV file.
    :param target_lang: A string indicating the target language for this TMX  
    :return: A list of TUs to be used in the creation of a new TMX
    
    """
    tu_list = []

    for row in csv_file:                                                                #Loops through every row in the csv
        if row["Base Value"] != "" and row["Translated Value"] != "":                   #Checks if both source and target has content
            
            source = row["Base Value"]                                                  #Assigns the value for the column "Base Value" as source
            
            target = row["Translated Value"]                                            #Assigns the value for the column "Translated Value" as Target
            
            src_tuv = PythonTmx.Tuv(xmllang="en-us")                                    #Constructs the source TUV using the value 
            src_tuv.segment.text = source                                               #of source, and "en-us" as language
            
            tgt_tuv = PythonTmx.Tuv(xmllang=language_codes.get(target_lang))            #Constructs the target TUV using the value 
            tgt_tuv.segment.text = target                                               #of target, and a match from language_codes as language
            
            tu_list.append(PythonTmx.Tu(srclang="en-us", tuvs=[src_tuv,tgt_tuv]))       #Creates a new TU using the previously defined TUVs and adds it  
                                                                                        #to tu_list    
    print("\tNumber of entries: " + str(len(tu_list)))

    return tu_list                                                                      #After creating each TU from the file, returns a list of TUs

    
def main():
    csv_files = glob.glob("*.csv")                                                      #This list will store every file name with the ".csv" extension

    for csv1 in csv_files:                                                              #Loops through every csv name
        with open(csv1, newline='', encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile,)
            print("\tconverting " + csv1)
            tmx_list = csv_converter(reader, csv1.replace(".csv", ""))                  #Generates a list of TUs using a CSV file, and its name
                                                                                        #as a parameter for the target language

            clean_tm_object = PythonTmx.Tmx(tus=tmx_list)                               #Creates a new TMX from every csv on the list

            clean_tm_object.header = PythonTmx.Header(creationdate=datetime.today())    #Since there is no original header, a new one is created with the
                                                                                        #creationdate as its only value
            clean_tm_object.to_tmx(csv1.replace(".csv", ".tmx"))
            print("\tclean TM has been created\n")
            csvfile.close()


if __name__ == "__main__":
    main()