from langdetect import detect
from characterai import aiocai, sendCode, authUser
import asyncio
import time
import nltk
import dl_translate as dlt
from IPython.display import HTML, display
import random
from ipywidgets import widgets
import os

async def warn(msg, text_color, icon_url):
    display(HTML(f'''
        <div style="width:100%;margin:10px auto;text-align:center;">
            <img src="{icon_url}" style="vertical-align:middle;margin-right:5px;width:30px;height:30px;">
            <strong style="font-size:20px; color: {text_color}; vertical-align:middle;">{msg}</strong>
        </div>
    '''))

async def get_character(client, prompt):
    try:
        ipt = input(prompt).strip().replace(" ", "+")
        query_char = await client.search(ipt)
        print(f'\nPersonagens encontrados:\n')
        for index, char in zip(range(NUM_RESULTADOS_BUSCA), query_char):
            print(f'({index}): {char.participant__name} - {char.participant__num_interactions} interações\n"{char.title}"\n')
        char_index = int(input("Selecione um número: "))
        clear_console()
        return query_char[char_index].external_id, PATH_AVATAR + query_char[char_index].avatar_file_name
    except Exception as e:
        print(f"Erro ao buscar personagem: {e}")
        return False

async def initialize_chat(client, char_id, user_id):
    try:
        chat, answer = await client.new_chat(char_id, user_id)
        time.sleep(WAIT_TIME)
        return chat, answer
    except Exception as e:
        print(f"Erro ao inicializar o chat: {e}")
        return False, False

def naturalizar_mensagem(mensagem): #limite de frases por parágrafo
    num_pgfs = random.choice([2, 3]);
    sent_tokenizer = nltk.data.load('tokenizers/punkt/portuguese.pickle')
    frases = sent_tokenizer.tokenize(mensagem)

    paragrafos = []
    for i in range(0, len(frases), num_pgfs):
        paragrafo = ' '.join(frases[i:i+num_pgfs])
        paragrafos.append(paragrafo)

    texto_formatado = '<br/><br/>'.join(paragrafos)
    return texto_formatado

async def render_chat_bubble(name, message, avatar, direction, timestamp):
    bubble_html = f'''
    <div class="message-wrapper {direction}">
        <img class="profile-pic" src="{avatar}" alt="{name}">
        <div class="chat-bubble">
            <div class="message-detail">
                <span class="bold">{name}</span> <span class="timestamp">{timestamp}</span>
            </div>
            <div class="message">{naturalizar_mensagem(message)}</div>
        </div>
    </div>
    '''

    bubble_style = '''
    <style>
        .message-wrapper {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .message-wrapper.left {
            justify-content: flex-start;
        }
        .message-wrapper.right {
            flex-direction: row-reverse;
        }
        .profile-pic {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            margin: 0 10px;
        }
        .chat-bubble {
            border-radius: 5px;
            display: inline-block;
            padding: 10px 18px;
            max-width: 50%;
            position: relative;
        }
        .chat-bubble:before {
            content: "";
            position: absolute;
            width: 0;
            height: 0;
            border: 10px solid transparent;
            top: 50%;
            transform: translateY(-50%);
        }
        .message-wrapper.left .chat-bubble {
            background-color: #e6e5eb;
            margin-left: 10px;
            color: #000;
        }
        .message-wrapper.left .chat-bubble:before {
            left: -10px;
            border-right-color: #e6e5eb;
            border-left: 0;
        }
        .message-wrapper.right .chat-bubble {
            background-color: #158ffe;
            color: #fff;
            margin-right: 10px;
        }
        .message-wrapper.right .chat-bubble:before {
            right: -10px;
            border-left-color: #158ffe;
            border-right: 0;
        }
        .message {
            font-size: 16px;
        }
        .message-detail {
            white-space: nowrap;
            font-size: 16px;
            margin-bottom: 5px;
        }
        .bold {
            font-weight: bold;
        }
        .timestamp {
            font-size: 12px;
        }
    </style>
    '''
    display(HTML(bubble_html + bubble_style))

async def traduzir_mensagem(mensagem):
    try:
        lang = detect(mensagem)
        if lang != 'pt':
          mt = dlt.TranslationModel()
          linguagens_abbr = mt.get_lang_code_map()
          for linguagem, abbr in linguagens_abbr.items():
            if abbr == lang:
              sentencas = nltk.tokenize.sent_tokenize(mensagem, linguagem.lower())
              return " ".join(mt.translate(sentencas, source=lang, target='pt'))
        return mensagem
    except Exception as e:
        print(f"Erro ao traduzir mensagem: {e}")
        return mensagem

def clear_console():
    if os.name == 'nt':
        os.system('cls')
    else:  
        os.system('clear')

async def main():
    try:
        print("Testando seu TOKEN...")
        client = aiocai.Client(API_KEY)
        me = await client.get_me()
        print("TOKEN autenticado com sucesso!")
        char1, avatar_char1 = await get_character(client, "Insira o nome do primeiro personagem: ")
        if char1 == False:
          return False

        char2, avatar_char2 = await get_character(client, "Insira o nome do segundo personagem: ")
        if char2 == False:
          return False

        tema = input("Gostaria de TENTAR escolher um tema? (vazio para não): ")
        if tema:
            tema = f"\n\nMas preste atenção! O tema dessa conversa é: {tema}"
        clear_console()
        print("Realizando preparativos...\n")

        async with await client.connect() as chat:
            new_chat1, answer1 = await initialize_chat(chat, char1, me.id)
            new_chat2, answer2 = await initialize_chat(chat, char2, me.id)
            if new_chat1 == False or new_chat2 == False:
              return False

            msg_inicial = await traduzir_mensagem(answer2.text)
            await render_chat_bubble(answer2.name, msg_inicial, avatar_char2, 'left', '(mensagem padrão traduzida)')
            await chat.send_message(char1, new_chat1.chat_id, PROMPT_CONTEXTO.format(receptor=answer2.name, aviso_tema=tema))
            await chat.send_message(char2, new_chat2.chat_id, PROMPT_CONTEXTO.format(receptor=answer1.name, aviso_tema=tema))

            resp_char_1 = await chat.send_message(char1, new_chat1.chat_id, f'{answer2.name} disse: {msg_inicial}')
            time.sleep(WAIT_TIME)

            contador_mensagens = 0;
            while True:
                try:
                    if contador_mensagens < MAX_MSGS_FIND_NOT_PTBR and detect(resp_char_1.text) != "pt":
                      msg_traduzida = await traduzir_mensagem(resp_char_1.text)
                      await render_chat_bubble(resp_char_1.name, msg_traduzida, avatar_char1, 'right', '(mensagem traduzida)')
                      await chat.send_message(char1, new_chat1.chat_id, "(( LEMBRE-SE DE FALAR EM PORTUGUÊS BRASILEIRO!! ))")
                      time.sleep(WAIT_TIME)
                      resp_char_2 = await chat.send_message(char2, new_chat2.chat_id, PROMPT_CONVERSA.format(nome_locutor=resp_char_1.name, msg_locutor=resp_char_1.text))
                    else:
                      await render_chat_bubble(resp_char_1.name, resp_char_1.text, avatar_char1, 'right', '')
                      resp_char_2 = await chat.send_message(char2, new_chat2.chat_id, PROMPT_CONVERSA.format(nome_locutor=resp_char_1.name, msg_locutor=resp_char_1.text))

                    time.sleep(WAIT_TIME)
                    contador_mensagens+=1

                    if contador_mensagens < MAX_MSGS_FIND_NOT_PTBR and detect(resp_char_2.text) != "pt":
                      msg_traduzida = await traduzir_mensagem(resp_char_2.text)
                      await render_chat_bubble(resp_char_2.name, msg_traduzida, avatar_char2, 'left', '(mensagem traduzida)')
                      await chat.send_message(char2, new_chat2.chat_id, "(( LEMBRE-SE DE FALAR EM PORTUGUÊS BRASILEIRO!! ))")
                      time.sleep(WAIT_TIME)
                      resp_char_1 = await chat.send_message(char1, new_chat1.chat_id, PROMPT_CONVERSA.format(nome_locutor=resp_char_2.name, msg_locutor=msg_traduzida))
                    else:
                      await render_chat_bubble(resp_char_2.name, resp_char_2.text, avatar_char2, 'left', '')
                      resp_char_1 = await chat.send_message(char1, new_chat1.chat_id, PROMPT_CONVERSA.format(nome_locutor=resp_char_2.name, msg_locutor=resp_char_2.text))

                    time.sleep(WAIT_TIME)
                    contador_mensagens+=1
                except Exception as e:
                    print(f"Erro durante a troca de mensagens: {e}")
                    break
        return True
    except Exception as e:
        print(f"Erro no programa principal: {e}")
        return False

if __name__ == "__main__":
    # Constants
    WAIT_TIME = 1 # DELAY NO ENVIO DE CADA MENSAGEM, ÚTIL PARA EVITAR MAL ENTENDIDOS
    NUM_RESULTADOS_BUSCA = 6 # QUANTOS RESULTADOS APARECEM NA BUSCA POR UM PERSONAGEM
    MAX_MSGS_FIND_NOT_PTBR = 10 # QUANTAS MENSAGENS DA CONVERSA SERÃO CONFERIDAS SE A LINGUAGEM É PT-BR
    PROMPT_CONTEXTO = "((Você está conversando com {receptor}, enviarei suas mensagens para ele(a) e te direi a resposta dele(a). Começa a partir da próxima mensagem. Vamos falar em português brasileiro!)){aviso_tema}"
    PROMPT_CONVERSA = "{nome_locutor} disse: {msg_locutor}"
    PATH_AVATAR = "https://characterai.io/i/80/static/avatars/" # ROTA ONDE O CAI GUARDA AS IMAGENS DOS AVATARES NO SERVIDOR
    API_KEY = os.getenv("TOKEN_BATEPAPO")  # Obtém a API Key de uma variável de ambiente
    if not API_KEY:
        API_KEY = input("Insira o seu TOKEN do Character AI: ")

    # Baixar o pacote 'punkt'
    nltk.download('punkt_tab')
    
    print(asyncio.run(traduzir_mensagem("This is a test message just to check if the translation is working properly...")))
    success = False
    while success == False:
        success = asyncio.run(main())