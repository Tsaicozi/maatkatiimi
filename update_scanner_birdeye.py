#!/usr/bin/env python3
"""
Päivitä Token Scanner käyttämään Birdeye Key Manager -integraatiota
"""

import asyncio
import sys
from pathlib import Path

def update_scanner_file(file_path: str):
    """Päivitä scanner-tiedosto käyttämään Birdeye-integraatiota"""
    
    scanner_file = Path(file_path)
    if not scanner_file.exists():
        print(f"❌ Tiedostoa {file_path} ei löydy")
        return False
    
    print(f"📝 Päivitetään {file_path}...")
    
    # Lue nykyinen koodi
    code = scanner_file.read_text()
    original_code = code
    
    # 1. Lisää import jos puuttuu
    if "from birdeye_integration import birdeye" not in code:
        # Etsi sopiva paikka importille
        lines = code.split('\n')
        import_added = False
        
        for i, line in enumerate(lines):
            # Lisää muiden importtien jälkeen
            if line.startswith("from dotenv import"):
                lines.insert(i + 1, "from birdeye_integration import birdeye")
                import_added = True
                break
            elif line.startswith("import aiohttp"):
                lines.insert(i + 1, "from birdeye_integration import birdeye")
                import_added = True
                break
        
        if not import_added:
            # Lisää alkuun jos ei löytynyt sopivaa paikkaa
            for i, line in enumerate(lines):
                if not line.startswith("#") and line.strip():
                    lines.insert(i, "from birdeye_integration import birdeye\n")
                    break
        
        code = '\n'.join(lines)
        print("  ✅ Lisätty birdeye_integration import")
    
    # 2. Päivitä __init__ metodi
    if "self.birdeye_integration = None" not in code:
        # Etsi __init__ metodi
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if "def __init__(self" in line:
                # Etsi sopiva paikka __init__ sisällä
                j = i + 1
                while j < len(lines):
                    if "self.session" in lines[j]:
                        lines.insert(j + 1, "        self.birdeye_integration = None  # Will be initialized in __aenter__")
                        break
                    elif "self.logger" in lines[j]:
                        lines.insert(j + 1, "        self.birdeye_integration = None  # Will be initialized in __aenter__")
                        break
                    j += 1
                break
        code = '\n'.join(lines)
        print("  ✅ Lisätty birdeye_integration attribuutti")
    
    # 3. Päivitä __aenter__ metodi
    if "await birdeye.initialize()" not in code:
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if "async def __aenter__" in line:
                # Etsi self.session luonti
                j = i + 1
                while j < len(lines):
                    if "self.session = aiohttp.ClientSession" in lines[j]:
                        # Lisää birdeye alustus sen jälkeen
                        lines.insert(j + 1, "        # Alusta Birdeye integraatio")
                        lines.insert(j + 2, "        try:")
                        lines.insert(j + 3, "            await birdeye.initialize()")
                        lines.insert(j + 4, "            self.birdeye_integration = birdeye")
                        lines.insert(j + 5, "            self.logger.info('✅ Birdeye integration alustettu')")
                        lines.insert(j + 6, "        except Exception as e:")
                        lines.insert(j + 7, "            self.logger.warning(f'⚠️ Birdeye integration epäonnistui: {e}')")
                        lines.insert(j + 8, "            self.birdeye_integration = None")
                        break
                    j += 1
                break
        code = '\n'.join(lines)
        print("  ✅ Lisätty Birdeye alustus")
    
    # 4. Päivitä _scan_birdeye metodi käyttämään integraatiota
    if "async def _scan_birdeye" in code:
        print("  📝 Päivitetään _scan_birdeye metodi...")
        
        # Etsi metodin alku ja loppu
        lines = code.split('\n')
        method_start = None
        method_end = None
        
        for i, line in enumerate(lines):
            if "async def _scan_birdeye" in line:
                method_start = i
                # Etsi metodin loppu (seuraava def tai class)
                indent = len(line) - len(line.lstrip())
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() and not lines[j].startswith(' ' * (indent + 1)):
                        if lines[j].startswith(' ' * indent) and ('def ' in lines[j] or 'async def' in lines[j]):
                            method_end = j
                            break
                    j += 1
                if method_end is None:
                    method_end = len(lines)
                break
        
        if method_start is not None:
            # Luo uusi metodi
            new_method = [
                "    async def _scan_birdeye(self) -> List[RealSolanaToken]:",
                '        """Skannaa Birdeye API:sta käyttäen Key Manager -integraatiota"""',
                "        tokens = []",
                "        ",
                "        # Käytä integraatiota jos saatavilla",
                "        if self.birdeye_integration:",
                "            try:",
                "                # Hae uudet tokenit",
                "                new_tokens = await self.birdeye_integration.get_new_tokens(limit=50)",
                "                ",
                "                if new_tokens:",
                "                    for token_data in new_tokens[:20]:  # Top 20",
                "                        try:",
                "                            # Hae lisätiedot",
                "                            mint = token_data.get('address', '')",
                "                            if not mint:",
                "                                continue",
                "                            ",
                "                            # Hae turvallisuustiedot",
                "                            security = await self.birdeye_integration.get_token_security(mint)",
                "                            ",
                "                            # Luo token objekti",
                "                            token = RealSolanaToken(",
                "                                mint_address=mint,",
                "                                symbol=token_data.get('symbol', 'Unknown'),",
                "                                name=token_data.get('name', 'Unknown Token'),",
                "                                price=float(token_data.get('price', 0)),",
                "                                market_cap=float(token_data.get('mc', 0)),",
                "                                liquidity=float(token_data.get('liquidity', 0)),",
                "                                volume_24h=float(token_data.get('v24hUSD', 0)),",
                "                                created_at=token_data.get('createdAt', ''),",
                "                                dex='birdeye',",
                "                                pair_address=token_data.get('poolAddress', ''),",
                "                                price_change_24h=float(token_data.get('priceChange24h', 0)),",
                "                                holder_count=security.get('data', {}).get('holderCount', 0) if security else 0,",
                "                                top_10_holders=security.get('data', {}).get('top10HoldersPercent', 0) if security else 0,",
                "                                is_mutable=security.get('data', {}).get('mintAuthority', None) is not None if security else True,",
                "                                is_freezable=security.get('data', {}).get('freezeAuthority', None) is not None if security else True",
                "                            )",
                "                            tokens.append(token)",
                "                            ",
                "                        except Exception as e:",
                "                            self.logger.debug(f'Virhe tokenin käsittelyssä: {e}')",
                "                            continue",
                "                            ",
                "                    self.logger.info(f'✅ Birdeye (integrated): {len(tokens)} tokenia')",
                "                else:",
                "                    self.logger.info('Birdeye: Ei uusia tokeneita')",
                "                    ",
                "            except Exception as e:",
                "                self.logger.warning(f'Birdeye integration virhe: {e}')",
                "                # Fallback vanhaan tapaan jos integraatio epäonnistuu",
                "                return await self._scan_birdeye_legacy()",
                "        else:",
                "            # Käytä vanhaa tapaa jos integraatio ei saatavilla",
                "            return await self._scan_birdeye_legacy()",
                "            ",
                "        return tokens",
                "    ",
                "    async def _scan_birdeye_legacy(self) -> List[RealSolanaToken]:",
                '        """Vanha Birdeye skannaus (fallback)"""',
                "        # Säilytä vanha koodi tässä fallbackina",
                "        return []"
            ]
            
            # Korvaa vanha metodi uudella
            lines = lines[:method_start] + new_method + lines[method_end:]
            code = '\n'.join(lines)
            print("  ✅ Päivitetty _scan_birdeye metodi")
    
    # 5. Tallenna jos muutoksia
    if code != original_code:
        # Varmuuskopio
        backup_path = scanner_file.with_suffix('.py.backup')
        scanner_file.rename(backup_path)
        print(f"  📋 Varmuuskopio: {backup_path}")
        
        # Tallenna päivitetty koodi
        scanner_file.write_text(code)
        print(f"  ✅ Tallennettu päivitetty {file_path}")
        return True
    else:
        print(f"  ℹ️ Ei muutoksia tarvita")
        return False


async def test_updated_scanner():
    """Testaa päivitetty scanner"""
    print("\n🧪 Testataan päivitettyä scanneria...")
    
    try:
        # Import scanner
        from real_solana_token_scanner import RealSolanaTokenScanner
        
        async with RealSolanaTokenScanner() as scanner:
            # Tarkista integraatio
            if hasattr(scanner, 'birdeye_integration') and scanner.birdeye_integration:
                print("✅ Birdeye integration löytyy")
                
                # Testaa skannaus
                tokens = await scanner._scan_birdeye()
                print(f"✅ Skannattu {len(tokens)} tokenia")
                
                if tokens:
                    print("\n📊 Esimerkkitokeneita:")
                    for token in tokens[:3]:
                        print(f"  - {token.symbol}: ${token.price:.6f}")
            else:
                print("⚠️ Birdeye integration puuttuu")
                
    except Exception as e:
        print(f"❌ Testaus epäonnistui: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("=" * 60)
    print("🔧 BIRDEYE SCANNER INTEGRATION UPDATER")
    print("=" * 60)
    
    # Lista päivitettävistä tiedostoista
    scanner_files = [
        "real_solana_token_scanner.py",
        "enhanced_token_scanner.py",
        "optimized_token_scanner.py",
        "nextgen_token_scanner_bot.py"
    ]
    
    updated_count = 0
    
    for file in scanner_files:
        if Path(file).exists():
            print(f"\n📄 Käsitellään: {file}")
            if update_scanner_file(file):
                updated_count += 1
        else:
            print(f"\n⏭️ Ohitetaan: {file} (ei löydy)")
    
    print("\n" + "=" * 60)
    print(f"✅ Päivitetty {updated_count} tiedostoa")
    
    if updated_count > 0:
        # Testaa päivitetty scanner
        await test_updated_scanner()
    
    print("\n" + "=" * 60)
    print("✅ VALMIS!")
    print("\nVoit nyt käynnistää scannerin:")
    print("  python3 real_solana_token_scanner.py")
    print("\nTai testata:")
    print("  python3 -m real_solana_token_scanner")


if __name__ == "__main__":
    asyncio.run(main())