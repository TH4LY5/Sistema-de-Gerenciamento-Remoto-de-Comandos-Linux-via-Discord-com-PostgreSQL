# security.py
import re


class CommandSecurity:
    # Lista de padrões perigosos (regex) - Atualizada
    DANGEROUS_PATTERNS = [
        # Comandos de exclusão destrutiva
        r'rm\s+-(rf|fr)\s+/($|\s)',
        r'rm\s+-(rf|fr)\s+\.($|\s)',
        r'rm\s+-(rf|fr)\s+\*($|\s)',
        r'rm\s+-(rf|fr)\s+~/($|\s)',
        r'rm\s+-(rf|fr)\s+/home/($|\s)',

        # Comandos de destruição de disco
        r'dd\s+if=.*\s+of=/dev/(sd|hd|nvme)',
        r'mkfs\.\w+\s+/dev/(sd|hd|nvme)',
        r'fdisk\s+/dev/(sd|hd|nvme)',

        # Comandos de sistema perigosos
        r'shutdown\s+-(h|now)',
        r'poweroff',
        r'reboot',
        r'init\s+0',
        r'kill\s+-9\s+-1',
        r'pkill\s+-9\s+-U\s+0',

        # Manipulação de permissões perigosas
        r'chmod\s+-(R|r)\s+0+0+0\s+/',
        r'chown\s+-(R|r)\s+(nobody|root):(nogroup|root)\s+/',

        # Comandos de rede perigosos - CORRIGIDOS
        r'iptables\s+.*(-F|--flush)',
        r'iptables\s+.*-X',  # Deleta chains personalizadas
        r'iptables\s+.*-P\s+INPUT\s+ACCEPT',  # Aceita todo tráfego
        r'ufw\s+disable',
        r'nc\s+-l\s+-p\s+\d+\s+-e\s+/bin/(bash|sh)',
        r'socat\s+TCP-LISTEN:\d+\s+EXEC:/bin/(bash|sh)',

        # Injeção de código remoto
        r'(curl|wget)\s+.*\s+\|?\s*(bash|sh)',

        # Bombas de fork
        r':\(\)\{.*:\|:.*\}.*;.*:',
        r'while\s+true.*do.*:.*done',

        # Elevação de privilégio
        r'sudo\s+su',
        r'sudo\s+-i',

        # Novos padrões descobertos
        r'iptables\\s\+F',  # Para capturar a tentativa com escape
        r'iptables.*flush',
    ]

    @classmethod
    def is_dangerous(cls, command):
        """Verifica se um comando é perigoso"""
        # Normaliza o comando: remove espaços extras e converte para minúsculas
        normalized_cmd = ' '.join(command.split()).lower()

        # Verifica padrões perigosos
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, normalized_cmd, re.IGNORECASE):
                return True

        # Verifica comandos que começam com padrões perigosos
        dangerous_starts = [
            'rm -rf /', 'rm -rf ~', 'rm -rf .', 'rm -rf *',
            'dd if=', 'mkfs.', 'chmod 000', 'chown nobody:nogroup /',
            'iptables -f', 'iptables --flush', 'iptables -x', 'iptables -p input accept'
        ]

        for dangerous_start in dangerous_starts:
            if normalized_cmd.startswith(dangerous_start.lower()):
                return True

        return False