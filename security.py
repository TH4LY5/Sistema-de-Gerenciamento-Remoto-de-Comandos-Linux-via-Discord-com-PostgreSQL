import re
from typing import List


class CommandSecurity:
    # Padrões perigosos melhorados
    DANGEROUS_PATTERNS = [
        # Comandos de exclusão destrutiva - melhorados
        r'(^|\s|;|&&|\|\|)rm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)/(?:\s|$|&)',
        r'(^|\s|;|&&|\|\|)rm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)\.(?:\s|$|&)',
        r'(^|\s|;|&&|\|\|)rm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)\*(?:\s|$|&)',
        r'(^|\s|;|&&|\|\|)rm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)~/(?:\s|$|&)',
        r'(^|\s|;|&&|\|\|)rm\s+-(r|f|rf|fr|r\s+f|f\s+r)[^\n]*(?:\s|^)/home/(?:\s|$|&)',

        # Comandos de destruição de disco - melhorados
        r'(^|\s|;|&&|\|\|)dd\s+[^\n]*of\s*=\s*/dev/(sd|hd|nvme|sda|sdb|sdc|vda|vdb)',
        r'(^|\s|;|&&|\|\|)mkfs\.\w*\s+[^\n]*/dev/(sd|hd|nvme|sda|sdb|sdc|vda|vdb)',
        r'(^|\s|;|&&|\|\|)fdisk\s+[^\n]*/dev/(sd|hd|nvme|sda|sdb|sdc|vda|vdb)',
        r'(^|\s|;|&&|\|\|)mkfs\s*$',  # Comando mkfs sem parâmetros

        # Comandos de sistema perigosos - melhorados
        r'(^|\s|;|&&|\|\|)shutdown\s+-(h|now|halt|poweroff)',
        r'(^|\s|;|&&|\|\|)poweroff\b',
        r'(^|\s|;|&&|\|\|)reboot\b',
        r'(^|\s|;|&&|\|\|)init\s+[06]',
        r'(^|\s|;|&&|\|\|)kill\s+-(9|KILL)\s+(-1|-\s*1)',
        r'(^|\s|;|&&|\|\|)pkill\s+-(9|KILL)\s+-(U|user)\s+0',

        # Manipulação de permissões perigosas - melhorados
        r'(^|\s|;|&&|\|\|)chmod\s+-(R|r|recursive)\s+[0-7][0-7][0-7]\s+/',
        r'(^|\s|;|&&|\|\|)chown\s+-(R|r|recursive)\s+(nobody|root|0):(nogroup|root|0)\s+/',

        # Comandos de rede perigosos - melhorados
        r'(^|\s|;|&&|\|\|)iptables\s+[^\n]*-(F|X|flush)',
        r'(^|\s|;|&&|\|\|)iptables\s+[^\n]*-P\s+(INPUT|OUTPUT|FORWARD)\s+ACCEPT',
        r'(^|\s|;|&&|\|\|)ufw\s+(disable|reset)',
        r'(^|\s|;|&&|\|\|)nc\s+[^\n]*-l[^\n]*-e\s+/bin/(bash|sh|zsh)',
        r'(^|\s|;|&&|\|\|)socat\s+[^\n]*TCP-LISTEN[^\n]*EXEC:/bin/(bash|sh|zsh)',

        # Injeção de código remoto - melhorados
        r'(^|\s|;|&&|\|\|)(curl|wget)\s+[^\n]*(?:\s|\|)(bash|sh|zsh|python|perl)(?:\s|$|&)',
        r'(^|\s|;|&&|\|\|)(bash|sh|zsh)\s+<(\(|\))(curl|wget)',

        # Bombas de fork - melhorados
        r':\(\)\s*\{\s*:\s*\|\s*:\s*.*\}\s*;\s*:',
        r'while\s+(?:true|:)\s*;?\s*do\s+(?:.+;?\s*)?done',

        # Elevação de privilégio - melhorados
        r'(^|\s|;|&&|\|\|)sudo\s+(su|bash|sh|zsh|python|perl)',
        r'(^|\s|;|&&|\|\|)sudo\s+-(i|S|s)',

        # Novos padrões
        r'(^|\s|;|&&|\|\|)mv\s+[^\n]*/(?:\.\.|dev|etc|home|root|usr|var|proc|sys)(?:\s|$)',
        r'(^|\s|;|&&|\|\|)cat\s+[>\|]\s*/dev/(sd|hd|nvme|sda|sdb)',
        r'(^|\s|;|&&|\|\|)echo\s+[^\n]*>[^\n]*/(?:\.\.|dev|etc|home|root|usr|var|proc|sys)',
    ]

    # Comandos perigosos que devem ser bloqueados completamente
    DANGEROUS_COMMANDS = [
        'rm -rf /', 'rm -rf /*', 'rm -rf ~', 'rm -rf .', 'rm -rf *',
        'dd if=', 'mkfs.', 'chmod 000', 'chown nobody:nogroup /',
        'iptables -F', 'iptables --flush', 'iptables -X',
        'iptables -P INPUT ACCEPT', 'ufw disable', 'mkfs'
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

        return False