import re
from typing import List

class CommandSecurity:
    # Padrões perigosos melhorados com regex mais abrangentes
    DANGEROUS_PATTERNS = [
        # Comandos de exclusão destrutiva - melhorados
        r'\brm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)/(?:\s|$)|^\s*rm\s+-(r|f|rf|fr)[^\n]*/\s*',
        r'\brm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)\.(?:\s|$)|^\s*rm\s+-(r|f|rf|fr)[^\n]*\.\s*',
        r'\brm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)\*(?:\s|$)|^\s*rm\s+-(r|f|rf|fr)[^\n]*\*\s*',
        r'\brm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)~/(?:\s|$)|^\s*rm\s+-(r|f|rf|fr)[^\n]*~/\s*',
        r'\brm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)/home/(?:\s|$)|^\s*rm\s+-(r|f|rf|fr)[^\n]*/home/\s*',
        
        # Comandos de destruição de disco - melhorados
        r'\bdd\s+[^\n]*of\s*=\s*/dev/(sd|hd|nvme|sda|sdb|sdc|vda|vdb)',
        r'\bmkfs\.\w+\s+[^\n]*/dev/(sd|hd|nvme|sda|sdb|sdc|vda|vdb)',
        r'\bfdisk\s+[^\n]*/dev/(sd|hd|nvme|sda|sdb|sdc|vda|vdb)',
        
        # Comandos de sistema perigosos - melhorados
        r'\bshutdown\s+-(h|now|halt|poweroff)|\bshutdown\s+now\b',
        r'\bpoweroff\b|\bhalt\b',
        r'\breboot\b',
        r'\binit\s+[06]',
        r'\bkill\s+-(9|KILL)\s+(-1|-\s*1|\$\(pidof\s+\w+\)|\$\(pgrep\s+\w+\))',
        r'\bpkill\s+-(9|KILL)\s+-(U|user)\s+0',
        
        # Manipulação de permissões perigosas - melhorados
        r'\bchmod\s+-(R|r|recursive)\s+[0-7][0-7][0-7]\s+/',
        r'\bchown\s+-(R|r|recursive)\s+(nobody|root|0):(nogroup|root|0)\s+/',
        
        # Comandos de rede perigosos - melhorados
        r'\biptables\s+[^\n]*-(F|X|flush)',
        r'\biptables\s+[^\n]*-P\s+(INPUT|OUTPUT|FORWARD)\s+ACCEPT',
        r'\bufw\s+(disable|reset)',
        r'\bnc\s+[^\n]*-l[^\n]*-e\s+/bin/(bash|sh|zsh)',
        r'\bsocat\s+[^\n]*TCP-LISTEN[^\n]*EXEC:/bin/(bash|sh|zsh)',
        
        # Injeção de código remoto - melhorados
        r'(?:^|\s|;|&&|\|\|)(curl|wget)\s+[^\n]*(?:\s|\|)(bash|sh|zsh|python|perl)(?:\s|$|&)',
        r'(?:^|\s|;|&&|\|\|)(bash|sh|zsh)\s+<(?:\(|\))(curl|wget)',
        
        # Bombas de fork - melhorados
        r':\(\)\s*\{\s*:\s*\|\s*:\s*.*\}\s*;\s*:',
        r'while\s+(?:true|:)\s*;?\s*do\s+(?:.+;?\s*)?done',
        
        # Elevação de privilégio - melhorados
        r'\bsudo\s+(su|bash|sh|zsh|python|perl)',
        r'\bsudo\s+-(i|S|s)',
        
        # Novos padrões
        r'\bmv\s+[^\n]*/(?:\.\.|dev|etc|home|root|usr|var|proc|sys)(?:\s|$)',
        r'\bcat\s+[>\|]\s*/dev/(sd|hd|nvme|sda|sdb)',
        r'\becho\s+[^\n]*>[^\n]*/(?:\.\.|dev|etc|home|root|usr|var|proc|sys)',
    ]
    
    # Comandos perigosos que devem ser bloqueados completamente
    DANGEROUS_COMMANDS = [
        'rm -rf /', 'rm -rf /*', 'rm -rf ~', 'rm -rf .', 'rm -rf *',
        'dd if=', 'mkfs.', 'chmod 000', 'chown nobody:nogroup /',
        'iptables -F', 'iptables --flush', 'iptables -X', 
        'iptables -P INPUT ACCEPT', 'ufw disable'
    ]

    @classmethod
    def is_dangerous(cls, command: str) -> bool:
        """Verifica se um comando é perigoso com maior precisão"""
        # Normaliza o comando: remove espaços extras, tabulações e converte para minúsculas
        normalized_cmd = ' '.join(command.split()).lower()
        
        # Remove comentários (tudo após #)
        normalized_cmd = re.sub(r'#.*$', '', normalized_cmd)
        
        # Verifica comandos perigosos completos
        for dangerous_cmd in cls.DANGEROUS_COMMANDS:
            if dangerous_cmd in normalized_cmd:
                return True
        
        # Verifica padrões perigosos com regex
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, normalized_cmd, re.IGNORECASE | re.MULTILINE):
                return True
        
        # Verifica comandos que começam com padrões perigosos
        dangerous_starts = [
            'rm -rf /', 'rm -rf ~', 'rm -rf .', 'rm -rf *',
            'dd if=', 'mkfs.', 'chmod 000', 'chown nobody:nogroup /',
            'iptables -f', 'iptables --flush', 'iptables -x', 'iptables -p input accept'
        ]
        
        for dangerous_start in dangerous_starts:
            if normalized_cmd.startswith(dangerous_start):
                return True
        
        return False

    @classmethod
    def sanitize_command(cls, command: str) -> str:
        """Remove ou substitui partes perigosas de um comando"""
        # Lista de substituições seguras
        replacements = [
            (r'rm\s+-rf\s+/(?![^\s])', 'rm -rf /*'),  # Previne rm -rf /
            (r'rm\s+-(r|f|rf|fr)\s+\.\./', 'rm -rf ./*'),  # Previne rm -rf ../
            (r'chmod\s+0+0+0\s+/', 'chmod 000 /*'),  # Previne chmod 000 /
        ]
        
        sanitized = command
        for pattern, replacement in replacements:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            
        return sanitized