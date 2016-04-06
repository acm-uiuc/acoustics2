from pythonosc import osc_message_builder
from pythonosc import udp_client

client = udp_client.UDPClient("siebl-1104-07.acm.illinois.edu", 11662)

def switch_animation(anim):
    msg = osc_message_builder.OscMessageBuilder(address = "/switch")
    msg.add_arg(anim)
    msg = msg.build()
    client.send(msg)
    return {'message': 'Sent message for animation ' + str(anim)}
