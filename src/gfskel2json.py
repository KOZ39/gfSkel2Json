import json
import re
from struct import unpack

BLEND_MODE = (
    'normal',
    'additive',
    'multiply',
    'screen'
)
ATTACHMENT_TYPE = (
    'region',
    'boundingbox',
    'mesh',
    'skinnedmesh'
)

scale = 1
data = {}


class BinaryStream:
    def __init__(self, base_stream):
        self.base_stream = base_stream

    def readBool(self):
        return self.readByte() != b'\x00'

    def readByte(self):
        return self.base_stream.read(1)

    def readBytes(self, length):
        return self.base_stream.read(length)

    def readInt(self):
        b = ord(self.readByte())
        result = b & 0x7f
        if (b & 0x80):
            b = ord(self.readByte())
            result |= (b & 0x7f) << 7
            if (b & 0x80):
                b = ord(self.readByte())
                result |= (b & 0x7f) << 14
                if (b & 0x80):
                    b = ord(self.readByte())
                    result |= (b & 0x7f) << 21
                    if (b & 0x80):
                        b = ord(self.readByte())
                        result |= (b & 0x7f) << 28
                        result = -(0xffffffff + 1 - result)
        return result

    def readIntArray(self):
        array = []
        for i in range(self.readInt()):
            array.append(self.readInt())
        return array

    def readShort(self):
        return self.unpack('>H', 2)
    
    def readShortArray(self):
        array = []
        for i in range(self.readInt()):
            array.append(self.readShort())
        return array

    def readFloat(self):
        return self.unpack('>f', 4)

    def readFloatArray(self):
        n = self.readInt()
        array = []
        if scale == 1:
            for i in range(n):
                array.append(self.readFloat())
        else:
            for i in range(n):
                array.append(self.readFloat() * scale)
        return array

    def readString(self):
        length = self.readInt()
        if length == 0:
            return None 
        if length == 1:
            return ""
        length -= 1
        return self.unpack(str(length) + 's', length).decode()

    def readHex(self, length):
        return self.readBytes(length).hex()

    def unpack(self, fmt, length=1):
        return unpack(fmt, self.readBytes(length))[0]


def readSkin():
    if (slotCnt := stream.readInt()) == 0:
        return None
    skin = {}
    for i in range(slotCnt):
        slotIdx = stream.readInt()
        slot = {}
        for i in range(stream.readInt()):
            name = stream.readString()
            attachment = readAttachment(name)
            slot[name] = attachment
        skin[data['slots'][slotIdx]['name']] = slot
    return skin


def readAttachment(attachmentName):
    if (name := stream.readString()) is None:
        name = attachmentName
    at = ATTACHMENT_TYPE[stream.readInt()]
    if at == 'region':
        if (path := stream.readString()) is None:
            path = name
        region = {}
        region['type'] = 'region'
        region['name'] = name
        region['path'] = path
        region['x'] = stream.readFloat() * scale
        region['y'] = stream.readFloat() * scale
        region['scaleX'] = stream.readFloat()
        region['scaleY'] = stream.readFloat()
        region['rotation'] = stream.readFloat()
        region['width'] = stream.readFloat() * scale
        region['height'] = stream.readFloat() * scale
        region['color'] = stream.readHex(4)
        return region
    if at == 'boundingbox':
        box = {}
        box['type'] = 'boundingbox'
        box['name'] = name
        box['vertices'] = readFloatArray()
        return box
    if at == 'mesh':
        if (path := stream.readString()) is None:
            path = name
        mesh = {}
        mesh['type'] = 'mesh'
        mesh['name'] = name
        mesh['path'] = path
        mesh['uvs'] = stream.readFloatArray()
        mesh['triangles'] = stream.readShortArray()
        mesh['vertices'] = stream.readFloatArray()
        mesh['color'] = stream.readHex(4)
        mesh['hull'] = stream.readInt()
        if nonessential:
            mesh['edges'] = stream.readIntArray()
            mesh['width'] = stream.readFloat() * scale
            mesh['height'] = stream.readFloat() * scale
        return mesh
    if at == 'skinnedmesh':
        if (path := stream.readString()) is None:
            path = name
        skinnedmesh = {}
        skinnedmesh['type'] = 'skinnedmesh'
        skinnedmesh['name'] = name
        skinnedmesh['path'] = path
        skinnedmesh['uvs'] = stream.readFloatArray()
        skinnedmesh['triangles'] = stream.readShortArray()
        skinnedmesh['vertices'] = []
        for i in range(stream.readInt()):
            skinnedmesh['vertices'].append(stream.readFloat())
        skinnedmesh['color'] = stream.readHex(4)
        skinnedmesh['hull'] = stream.readInt()
        if nonessential:
            skinnedmesh['edges'] = stream.readIntArray()
            skinnedmesh['width'] = stream.readFloat() * scale
            skinnedmesh['height'] = stream.readFloat() * scale
        return skinnedmesh
    return None


def readAnimation():
    animation = {}
    duration = 0

    slots = {}
    for i in range(stream.readInt()):
        slotIdx = stream.readInt()
        slotMap = {}
        for j in range(stream.readInt()):
            timelineType = ord(stream.readByte())
            frameCnt = stream.readInt()
            if timelineType == 3:
                timeline = []
                for frameIdx in range(frameCnt):
                    timeline.append({})
                    timeline[frameIdx]['time'] = stream.readFloat()
                    timeline[frameIdx]['name'] = stream.readString()
                slotMap['attachment'] = timeline
                duration = max(duration, timeline[frameCnt-1]['time'])
            elif timelineType == 4:
                timeline = []
                for frameIdx in range(frameCnt):
                    timeline.append({})
                    timeline[frameIdx]['time'] = stream.eradFloat()
                    timeline[frameIdx]['color'] = stream.readHex(4)
                    if frameIdx < frameCnt - 1:
                       readCurve(frameIdx, timeline)
                slotMap['color'] = timeline
                duration = max(duration, timeline[frameCnt-1]['time'])
        slots[data['slots'][slotIdx]['name']] = slotMap
    animation['slots'] = slots

    bones = {}
    for i in range(stream.readInt()):
        boneIdx = stream.readInt()
        boneMap = {}
        for j in range(stream.readInt()):
            timelineType = ord(stream.readByte())
            frameCnt = stream.readInt()
            if timelineType == 1:
                timeline = []
                for frameIdx in range(frameCnt):
                    timeline.append({})
                    timeline[frameIdx]['time'] = stream.readFloat()
                    timeline[frameIdx]['angle'] = stream.readFloat()
                    if frameIdx < frameCnt - 1:
                        readCurve(frameIdx, timeline)
                boneMap['rotate'] = timeline
                duration = max(duration, timeline[frameCnt-1]['time'])
            elif timelineType == 2 or timelineType == 0:
                timeline = []
                timelineScale = 1
                if timelineType == 2:
                    timelineScale = scale
                for frameIdx in range(frameCnt):
                    timeline.append({})
                    timeline[frameIdx]['time'] = stream.readFloat()
                    timeline[frameIdx]['x'] = stream.readFloat()                    
                    timeline[frameIdx]['y'] = stream.readFloat()
                    if frameIdx < frameCnt - 1:
                        readCurve(frameIdx, timeline)
                if timelineType == 0:
                    boneMap['scale'] = timeline
                else:
                    boneMap['translate'] = timeline
                duration = max(duration, timeline[frameCnt-1]['time'])
            elif timelineType == 5 or timelineType == 6:
                timeline = []
                for frameIdx in range(frameCnt):
                    timeline.append({})
                    timeline[frameIdx]['time'] = stream.readFloat()
                    if timelineType == 5:
                        timeline[frameIdx]['x'] = stream.readBool()
                    elif timelineType == 6:
                        timeline[frameIdx]['y'] = stream.readBool()
                if timelineType == 5:
                    boneMap['flipX'] = timeline
                else:
                    boneMap['flipY'] = timeline
                duration = max(duration, timeline[frameCnt-1]['time'])
            bones[data['bones'][boneIdx]['name']] = boneMap
        animation['bones'] = bones

    ik = {}
    for i in range(stream.readInt()):
        ikIdx = stream.readInt()
        frameCnt = stream.readInt()
        timeline = []
        for frameIdx in range(frameCnt):
            timeline.append({})
            timeline[frameIdx]['time'] = stream.readFloat()
            timeline[frameIdx]['mix'] = stream.readFloat()
            timeline[frameIdx]['bendPositive'] = stream.readBool()
            if frameIdx < frameCnt - 1:
                readCurve(frameIdx, timeline)
        ik[data[ikIdx]] = timeline
    animation['ik'] = ik

    ffd = {}
    for i in range(stream.readInt()):
        skinIdx = stream.readInt()
        slotMap = {}
        for j in range(stream.readInt()):
            slotIdx = stream.readInt()
            meshMap = {}
            for k in range(stream.readInt()):
                meshName = stream.readString()
                frameCnt = stream.readInt()
                attachment = None
                attachments = data['skins'][data['skinName'][skinIdx]]\
                              [data['slots'][slotIdx]['name']]
                for attachmentName in attachments:
                    if attachments[attachmentName]['name'] == meshName:
                        attachment = attachments[attachmentName]

                if not attachment:
                    print("FFD attachment not found: " + meshName);

                timeline = []
                for frameIdx in range(frameCnt):
                    time = stream.readFloat()
                    if attachment['type'] == 'mesh':
                        vertexCnt = len(attachment['vertices'])
                    else:
                        vertexCnt = len(attachment['uvs']) * 3 * 3
                        # This maybe wrong

                    vertices = []
                    for verticeIdx in range(vertexCnt):
                        vertices[verticeIdx] = 0.0

                    bugFixMultiplicator = 0.1

                    if (end := stream.readInt()) == 0:
                        if attachment['type'] == 'mesh':
                            for verticeIdx in range(vertexCnt):
                                vertices[verticeIdx] += attachment['vertices']\
                                                        [verticeIdx] * \
                                                        bugFixMultiplicator
                    else:
                        start = (v := stream.readInt())
                        end += start

                        while v < end:
                            vertices[v] = stream.readFloat() * scale
                            v += 1

                        if attachment['type'] == 'mesh':
                            meshVertices = attachment['vertices']
                            for v in range(len(vertices)):
                                vertices[v] += meshVertices[v] * \
                                               bugFixMultiplicator
                    timeline.append({})
                    timeline[frameIdx]['time'] = time
                    timeline[frameIdx]['vertices'] = vertices

                    if frameIdx < frameCnt - 1:
                        readCurve(frameIdx, timeline)
                meshMap[meshName] = timeline
                duration = max(duration, timeline[frameCnt-1]['time'])
            slotMap[data['slots'][slotIdx]['name']] = meshMap
        ffd[data['skinsName'][skinIdx]] = slotMap
    animation['ffd'] = ffd

    if (drawOrderCnt := stream.readInt()):
        drawOrders = []
        for i in range(drawOrderCnt):
            drawOrderMap = {}
            offsets = []
            for j in range(stream.readInt()):
                offsetMap = {}
                offsetMap['slot'] = data['slots'][stream.readInt()]['name'] 
                offsetMap['offset'] = stream.readInt()
                offsets.append(offsetMap)
            drawOrderMap['offsets'] = offsets
            drawOrderMap['time'] = stream.readFloat()
            drawOrders.append(drawOrderMap)
        duration = max(duration, drawOrders[drawOrderCnt-1]['time'])
        animation['drawOrder'] = drawOrders

    if (eventCnt := stream.readInt()):
        events = []
        for i in range(eventCnt):
            events.append({})
            time = stream.readFloat()
            events[i]['name'] = (name := data['eventsName'][stream.readInt()])
            events[i]['int'] = stream.readInt()
            events[i]['float'] = stream.readFloat()
            events[i]['string'] = stream.readString() if stream.readBool() \
                                  else ""
            events[i]['time'] = time
        duration = max(duration, events[eventCnt-1]['time'])
        animation['events'] = events
    return animation


def readCurve(frameIdx, timeline):
    if (curve := ord(stream.readByte())) == 1:
        timeline[frameIdx]['curve'] = 'stepped'
    elif curve == 2:
        timeline[frameIdx]['curve'] = [stream.readFloat(), stream.readFloat(), \
                                       stream.readFloat(), stream.readFloat()]


def repl(mo):
    x = str(mo.group())
    a, b = x.split('e-')
    c, d = a.split('.')
    return '0.' + '0' * (int(b)-1) + c + d


with open('Kalina.skel.txt', 'rb') as f:
    stream = BinaryStream(f)

    # skeleton
    data['skeleton'] = {}
    data['skeleton']['hash'] = stream.readString()
    data['skeleton']['spine'] = stream.readString()
    data['skeleton']['width'] = stream.readFloat()
    data['skeleton']['height'] = stream.readFloat()
    if (nonessential := stream.readBool()):
        data['skeleton']['images'] = stream.readString()

    # Bones
    data['bones'] = []
    for i in range(stream.readInt()):
        data['bones'].append({})
        data['bones'][i]['name'] = stream.readString()
        data['bones'][i]['parent'] =  None if (parentIdx := stream.readInt()-1) == -1 \
                                     else data['bones'][parentIdx]['name']
        data['bones'][i]['x'] = stream.readFloat() * scale
        data['bones'][i]['y'] = stream.readFloat() * scale
        data['bones'][i]['scaleX'] = stream.readFloat()
        data['bones'][i]['scaleY'] = stream.readFloat()
        data['bones'][i]['rotation'] = stream.readFloat()
        data['bones'][i]['length'] = stream.readFloat() * scale
        data['bones'][i]['flipX'] = stream.readBool()
        data['bones'][i]['flipY'] = stream.readBool()
        data['bones'][i]['inheritScale'] = stream.readBool()
        data['bones'][i]['inheritRotation'] = stream.readBool()
        if nonessential:
            data['bones'][i]['color'] = stream.readHex(4)

    # Ik Constraints
    if (ikIdx := stream.readInt()):
        data['ik'] = []
        for i in range(ikIdx):
            data['ik'].append({})
            data['ik']['name'] = stream.readString()
            data['ik']['bones'] = []
            for i in range(stream.readInt()):
                data['ik']['bones'].append(data['ik'][stream.readInt()]['name'])
            data['ik']['target'] = data['ik'][stream.readInt()]['name']
            data['ik']['mix'] = stream.readFloat()
            data['bendPositive'] = stream.readBool()

    # Slots
    data['slots'] = []
    for i in range(stream.readInt()):
        data['slots'].append({})
        data['slots'][i]['name'] = stream.readString()
        data['slots'][i]['bone'] = data['bones'][stream.readInt()]['name']
        data['slots'][i]['color'] = stream.readHex(4)
        data['slots'][i]['attachment'] = stream.readString()
        data['slots'][i]['blend'] = BLEND_MODE[stream.readInt()]

    # Default Skin
    data['skins'] = {}
    data['skinsName'] = []
    skins = {}
    if (defaultSkin := readSkin()) is not None:
        data['skins']['default'] = defaultSkin
        data['skinsName'].append('default')

    # Skin
    for i in range(stream.readInt()):
        skinName = readString()
        skin = stream.readSkin()
        skins[skinName] = skin
        data['skinsName'].append(skinName)

    # Events
    data['events'] = {}
    data['eventsName'] = []
    for i in range(stream.readInt()):
        eventName = stream.readString()
        data['events'][eventName] = {}
        data['events'][eventName]['int'] = stream.readInt()
        data['events'][eventName]['float'] = stream.readFloat()
        data['events'][eventName]['string'] = stream.readString()
        data['eventsName'].append(eventName)

    # Animations
    data['animations'] = {}
    for i in range(stream.readInt()):
        animationName = stream.readString()
        animation = readAnimation()
        data['animations'][animationName] = animation

data = json.dumps(data, indent=2)
data = re.sub(r'([\d]+)\.0([^\d]),?|-(0).0([^\d]+)', r'\1\2\3\4', data)
data = re.sub(r'([\d]+\.[\d]+e-[\d]+)', repl, data)

with open('Kalina.json', 'w') as f:
    f.write(data)
