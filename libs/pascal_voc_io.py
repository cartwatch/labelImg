#!/usr/bin/env python
# -*- coding: utf8 -*-

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs

XML_EXT = '.xml'
ENCODE_METHOD = 'utf-8'


class PascalVocWriter:
    def __init__(self, foldername, filename, imgSize, databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        tree = etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD)
        return tree.replace("  ".encode(), "\t".encode())
        # minidom does not support UTF-8
        '''reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="\t", encoding=ENCODE_METHOD)'''

    def genXML(self):
        """
            Return XML root
        """
        # Check conditions
        if self.filename is None or \
                self.foldername is None or \
                self.imgSize is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', 'yes')

        folder = SubElement(top, 'folder')
        folder.text = self.foldername

        filename = SubElement(top, 'filename')
        filename.text = self.filename

        if self.localImgPath is not None:
            localImgPath = SubElement(top, 'path')
            localImgPath.text = self.localImgPath

        source = SubElement(top, 'source')
        database = SubElement(source, 'database')
        database.text = self.databaseSrc

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        height.text = str(self.imgSize[0])
        width.text = str(self.imgSize[1])
        if len(self.imgSize) == 3:
            depth.text = str(self.imgSize[2])
        else:
            depth.text = '1'

        segmented = SubElement(top, 'segmented')
        segmented.text = '0'
        return top

    def addBndBox(self, xmin, ymin, xmax, ymax, name, attrs={}):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name

        bndbox.update(attrs)
        self.boxlist.append(bndbox)

    def appendObjects(self, top):
        for obj in self.boxlist:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            name.text = obj['name']

            pose = SubElement(object_item, 'pose')
            pose.text = "Unspecified"

            is_truncated = (
                int(obj['ymax']) == int(self.imgSize[0]) or
                int(obj['xmax']) == int(self.imgSize[1]) or
                int(obj['ymin']) == 1 or int(obj['xmin']) == 1
            )

            truncated = SubElement(object_item, 'truncated')
            truncated.text = parse_bool(is_truncated)

            bndbox = SubElement(object_item, 'bndbox')

            for key, value in obj.items():

                if key in ['xmin', 'ymin', 'xmax', 'ymax', 'name']:
                    e = SubElement(bndbox, key)
                    e.text = str(obj[key])
                elif key not in ['truncated', 'pose']:
                    attr = SubElement(object_item, str(key))
                    attr.text = parse_bool(value)

    def save(self, targetFile=None):
        root = self.genXML()
        self.appendObjects(root)
        out_file = None
        if targetFile is None:
            out_file = codecs.open(
                self.filename + XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)

        prettifyResult = self.prettify(root)
        out_file.write(prettifyResult.decode('utf8'))
        out_file.close()


class PascalVocReader:

    def __init__(self, filepath):
        # shapes type:
        # [label, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.size = {}
        self.filepath = filepath
        self.verified = False
        self.original_path = None

        try:
            self.parseXML()
        except Exception as e:
            print(e)

    def getShapes(self):
        return self.shapes

    def getSize(self):
        return self.size

    def parseXML(self):
        assert self.filepath.endswith(XML_EXT), "Unsupport file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xmltree = ElementTree.parse(self.filepath, parser=parser).getroot()
        # filename = xmltree.find('filename').text
        try:
            verified = xmltree.attrib['verified']
            if verified == 'yes':
                self.verified = True
        except KeyError:
            self.verified = False

        self.original_path = xmltree.find('path').text
        self.original_filename = xmltree.find('filename').text

        size = xmltree.find('size')
        self.size['width'] = int(size.find('width').text)
        self.size['height'] = int(size.find('height').text)
        self.size['depth'] = int(size.find('depth').text)

        for obj in xmltree.findall('object'):
            corners = dict(xmin=0, ymin=0, xmax=0, ymax=0)
            attrs = dict(difficult=False)

            for elem in obj.iter():
                t = elem.tag

                if t in ['bndbox', 'object']:
                    continue
                elif t in corners.keys():
                    corners[t] = int(elem.text)
                elif t == 'name':
                    label = elem.text
                elif t == 'pose':
                    attrs[t] = elem.text
                elif t == 'confidence':
                    attrs[t] = float(elem.text)
                else:
                    attrs[t] = bool(int(elem.text))

            points = [(corners['xmin'], corners['ymin']),
                      (corners['xmax'], corners['ymin']),
                      (corners['xmax'], corners['ymax']),
                      (corners['xmin'], corners['ymax'])]

            self.shapes.append((label, points, None, None, attrs))

        return True


def parse_bool(val):
    return str(int(bool(val)))
